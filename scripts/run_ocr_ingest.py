"""
scripts/run_ocr_ingest.py
─────────────────────────
Batch OCR + ChromaDB ingest for all PDF contracts in the dataset.

Usage:
    python scripts/run_ocr_ingest.py [--pack-dir PATH] [--force]

    --pack-dir  Path to contracts directory  (default: dataset/Pack/odin_dev_pack/bundle/contracts)
    --force     Re-ingest even if chunks already exist for a contract
"""

from __future__ import annotations
import argparse
import sys
import os
import time
from pathlib import Path

# ── ensure project root is importable ───────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ocr_ingest")

# ── PDF paths ────────────────────────────────────────────────────────────────
DEFAULT_CONTRACTS_DIR = ROOT / "dataset" / "Pack" / "odin_dev_pack" / "bundle" / "contracts"
EXTRA_PDFS = [ROOT / "dataset" / "Odin_PS.pdf"]


def get_contract_pdfs(contracts_dir: Path) -> list[Path]:
    pdfs = sorted(contracts_dir.glob("*.pdf")) if contracts_dir.exists() else []
    for extra in EXTRA_PDFS:
        if extra.exists() and extra not in pdfs:
            pdfs.append(extra)
    return pdfs


def ocr_pdf(pdf_path: Path) -> str:
    """Extract full text from a PDF using PyMuPDF + EasyOCR fallback."""
    from thor_agent.ocr_pdf import extract_text_from_pdf
    log.info("📄  OCR-extracting: %s", pdf_path.name)
    t0 = time.perf_counter()
    text = extract_text_from_pdf(pdf_path)
    elapsed = time.perf_counter() - t0
    char_count = len(text)
    log.info("    ✅  %s  →  %d chars  (%.1fs)", pdf_path.name, char_count, elapsed)
    if char_count < 20:
        log.warning("    ⚠️  Very little text extracted – PDF may be blank or corrupt.")
    return text


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """Split text into overlapping chunks for ChromaDB."""
    words = text.split()
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def ingest_to_chromadb(
    pdf_path: Path,
    text: str,
    force: bool = False,
) -> int:
    """Chunk the text and store into ChromaDB via ChunkStorage. Returns number of chunks added."""
    try:
        from thor_agent.storage import ChunkStorage
    except ImportError:
        log.error("Cannot import ChunkStorage – is the venv active?")
        return 0

    storage = ChunkStorage()
    contract_id = pdf_path.stem  # e.g. "B1", "STD", "A1"

    if not force:
        # Check if chunks already exist for this contract
        try:
            existing = storage.get_all_chunks()
            existing_for_contract = [c for c in existing if c.get("source") == contract_id]
            if existing_for_contract:
                log.info(
                    "    ⏭️  Skipping %s  – %d chunks already in ChromaDB  (use --force to re-ingest)",
                    contract_id, len(existing_for_contract),
                )
                return 0
        except Exception:
            pass  # proceed

    chunks = chunk_text(text)
    if not chunks:
        log.warning("    ⚠️  No text chunks generated for %s", contract_id)
        return 0

    log.info("    📦  Storing %d chunks for contract '%s'…", len(chunks), contract_id)

    added = 0
    for i, chunk in enumerate(chunks):
        try:
            chunk_id = f"{contract_id}_ocr_chunk_{i}"
            storage.store_chunk(
                chunk_id=chunk_id,
                document_id=contract_id,
                text=chunk,
                page_num=1,  # approximate; digital-text PDFs have pages merged
                source_type="contract",
                metadata={
                    "pdf_path": str(pdf_path),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "contract_id": contract_id,
                    "ingested_by": "run_ocr_ingest",
                },
            )
            added += 1
        except Exception as exc:
            log.error("    ❌  Failed to store chunk %d for %s: %s", i, contract_id, exc)

    log.info("    ✅  %d chunks stored for '%s'", added, contract_id)
    return added



def main() -> None:
    parser = argparse.ArgumentParser(description="Batch OCR + ChromaDB ingest for contract PDFs")
    parser.add_argument(
        "--pack-dir",
        type=Path,
        default=DEFAULT_CONTRACTS_DIR,
        help="Path to contracts PDF directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if chunks already exist for a contract",
    )
    args = parser.parse_args()

    pdfs = get_contract_pdfs(args.pack_dir)

    if not pdfs:
        log.error("❌  No PDFs found in %s", args.pack_dir)
        sys.exit(1)

    log.info("=" * 60)
    log.info("🔥  RAGNAROK OCR BATCH INGEST")
    log.info("    Found %d PDF(s) to process", len(pdfs))
    log.info("=" * 60)

    total_chunks = 0
    results: list[dict] = []

    for pdf_path in pdfs:
        log.info("")
        log.info("━" * 50)
        text = ocr_pdf(pdf_path)
        added = ingest_to_chromadb(pdf_path, text, force=args.force)
        total_chunks += added
        results.append({"pdf": pdf_path.name, "chars": len(text), "chunks_added": added})

    log.info("")
    log.info("=" * 60)
    log.info("🏆  OCR INGEST COMPLETE")
    log.info("=" * 60)
    log.info("")
    log.info("%-20s  %8s  %12s", "Contract", "Chars", "Chunks Added")
    log.info("%-20s  %8s  %12s", "─" * 20, "─" * 8, "─" * 12)
    for r in results:
        log.info("%-20s  %8d  %12d", r["pdf"], r["chars"], r["chunks_added"])
    log.info("")
    log.info("Total new chunks added to ChromaDB: %d", total_chunks)

    # Final count
    try:
        from thor_agent.storage import ChunkStorage
        storage = ChunkStorage()
        all_chunks = storage.get_all_chunks()
        log.info("Total chunks now in ChromaDB:       %d", len(all_chunks))
    except Exception:
        pass


if __name__ == "__main__":
    main()
