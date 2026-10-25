"""
scan_dataset.py
───────────────
Dataset Auto-Scanner for ODIN / Ragnarok
=========================================

Watches the `dataset/` folder (and all sub-folders) for new or modified PDF files.
When a PDF is detected it:
  1. Extracts text using PyMuPDF (fast native layer).
  2. Falls back to OCR via Thor's ocr_pdf module (PyMuPDF OCR) for scanned pages.
  3. POSTs the extracted text to the Ragnarok backend (/api/v1/workspace/upload-file).
  4. Prints a live status line so you can see every file that was processed.

Also performs an IMMEDIATE initial scan of every PDF already in the folder on startup.

Usage
─────
  python scan_dataset.py                    # watches dataset/
  python scan_dataset.py --dir dataset      # explicit path
  python scan_dataset.py --api http://...   # custom backend URL
  python scan_dataset.py --token YOUR_TOKEN # override auth token
  python scan_dataset.py --once             # scan once, then exit
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── colour helpers ─────────────────────────────────────────────────────────────
def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"

OK   = lambda t: _c("32;1", t)
ERR  = lambda t: _c("31;1", t)
WARN = lambda t: _c("33", t)
INFO = lambda t: _c("36", t)
DIM  = lambda t: _c("2", t)

# ── PDF text extraction ─────────────────────────────────────────────────────────
def extract_pdf_text(pdf_path: Path) -> str:
    """
    Extracts all text from a PDF using PyMuPDF.
    Falls back to PyMuPDF's built-in OCR (Tesseract integration) for blank pages.
    Returns plain text with page markers.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    parts: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()

        if not text:
            # Attempt PyMuPDF built-in OCR for scanned pages
            try:
                tp = page.get_textpage_ocr(language="eng", dpi=150, full=True)
                text = tp.extractText().strip()
            except Exception:
                text = ""

        if text:
            parts.append(f"# Page {page_num}\n{text}")

    doc.close()
    return "\n\n".join(parts)


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt"}

# ── backend ingestion ──────────────────────────────────────────────────────────
def ingest_file(file_path: Path, api_base: str, token: str) -> dict:
    """
    Uploads a file directly to the Ragnarok backend upload-file endpoint.
    Returns the JSON response dict.
    """
    import urllib.request
    import urllib.error

    url = f"{api_base.rstrip('/')}/api/v1/workspace/upload-file"
    boundary = "RagnarokBoundary1234"
    filename = file_path.name
    raw = file_path.read_bytes()

    mime_types = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".txt": "text/plain",
    }
    content_type = mime_types.get(file_path.suffix.lower(), "application/octet-stream")

    # Build multipart body
    body_parts = [
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        raw,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    body = b"".join(
        p.encode() if isinstance(p, str) else p for p in body_parts
    )

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
            "X-Odin-Client": "scanner",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            import json
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        import json
        body = exc.read().decode(errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = body
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


# ── single PDF processing ──────────────────────────────────────────────────────
_seen: dict[str, str] = {}  # path -> sha256 of raw bytes


def process_file(file_path: Path, api_base: str, token: str, *, quiet: bool = False) -> bool:
    """
    Process one file: hash-check → upload (backend handles text/OCR extraction).
    Returns True if ingested, False if skipped (duplicate or error).
    """
    raw = file_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:16]

    if _seen.get(str(file_path)) == sha:
        if not quiet:
            print(DIM(f"  ↩  skip (unchanged): {file_path.name}"))
        return False

    _seen[str(file_path)] = sha
    try:
        label = file_path.relative_to(file_path.parents[len(file_path.parts) - 2])
    except Exception:
        label = file_path.name

    print(INFO(f"\n📄 {label}"))
    print(DIM(f"   size={len(raw)//1024}KB  sha={sha}"))

    # Upload directly (backend handles text/OCR extraction)
    try:
        print(DIM("   → uploading to ODIN backend..."))
        result = ingest_file(file_path, api_base, token)
        key = result.get("document_key", "?")
        pages = result.get("pages") or "?"
        print(OK(f"   ✓ ingested → key={key}  pages={pages}"))
        return True

    except RuntimeError as exc:
        msg = str(exc)
        if "already exists" in msg.lower():
            print(WARN(f"   ⚠  already in ODIN: {file_path.name}"))
        else:
            print(ERR(f"   ✗ failed: {msg}"))
        return False

    except Exception as exc:
        print(ERR(f"   ✗ unexpected error: {exc}"))
        return False


# ── initial scan ───────────────────────────────────────────────────────────────
def scan_all(watch_dir: Path, api_base: str, token: str) -> int:
    files = sorted(p for p in watch_dir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS and p.is_file())
    if not files:
        print(WARN(f"No contract files found in {watch_dir}"))
        return 0
    print(INFO(f"\n🔍 Initial scan: found {len(files)} file(s) in {watch_dir}"))
    ingested = sum(
        1 for p in files if process_file(p, api_base, token, quiet=False)
    )
    print(INFO(f"\n✅ Initial scan complete: {ingested}/{len(files)} ingested"))
    return ingested


# ── watchdog file watcher ──────────────────────────────────────────────────────
def watch_loop(watch_dir: Path, api_base: str, token: str):
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class FileHandler(FileSystemEventHandler):
        def _handle(self, path_str: str):
            p = Path(path_str)
            if p.suffix.lower() in SUPPORTED_EXTENSIONS and p.is_file():
                time.sleep(0.5)  # let the write finish
                process_file(p, api_base, token)

        def on_created(self, event):
            if not event.is_directory:
                self._handle(event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                self._handle(event.src_path)

        def on_moved(self, event):
            self._handle(event.dest_path)

    observer = Observer()
    observer.schedule(FileHandler(), str(watch_dir), recursive=True)
    observer.start()
    print(INFO(f"\n👁  Watching {watch_dir} for new contracts/PDFs (Ctrl+C to stop)…\n"))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print(INFO("\n🛑 Watcher stopped."))
    observer.join()


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ODIN Dataset Auto-Scanner")
    parser.add_argument(
        "--dir", default="dataset",
        help="Folder to watch (default: dataset/)",
    )
    parser.add_argument(
        "--api", default="http://127.0.0.1:8000",
        help="Ragnarok API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get(
            "RAGNAROK_API_TOKEN",
            "8wkDxPPFyixSS6vVx2jWyEzt07Bfg_NDDxaDiO630jkHFC2EHQBshbm7NJO5ZJh_",
        ),
        help="API bearer token",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Scan existing files then exit (no watch loop)",
    )
    args = parser.parse_args()

    watch_dir = Path(args.dir).resolve()
    if not watch_dir.exists():
        print(ERR(f"Directory not found: {watch_dir}"))
        sys.exit(1)

    print(_c("35;1", "═" * 55))
    print(_c("35;1", " 🔱 ODIN Dataset Auto-Scanner"))
    print(_c("35;1", "═" * 55))
    print(DIM(f"   watch_dir : {watch_dir}"))
    print(DIM(f"   api_base  : {args.api}"))
    print(DIM(f"   token     : {args.token[:12]}…"))

    scan_all(watch_dir, args.api, args.token)

    if not args.once:
        watch_loop(watch_dir, args.api, args.token)


if __name__ == "__main__":
    main()
