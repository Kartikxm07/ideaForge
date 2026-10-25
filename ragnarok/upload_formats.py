"""Deterministic extraction for browser PDF, TXT, JSONL and image (OCR) uploads."""
from io import BytesIO
import json
from pathlib import Path
from typing import Literal

from pypdf import PdfReader
from pydantic import ValidationError

from .operational_events import OperationalEvent

MAX_UPLOAD_BYTES = 12_000_000
MAX_EXTRACTED_BYTES = 2_000_000


def safe_document_key(filename: str) -> str:
    stem = Path(filename).stem
    key = "".join(c if c.isascii() and (c.isalnum() or c in "._-") else "-" for c in stem).strip(".-_")[:80]
    if not key:
        raise ValueError("The file needs a usable name")
    return key


def decode_text(raw: bytes) -> str:
    if len(raw) > MAX_EXTRACTED_BYTES:
        raise ValueError("Text exceeds the 2 MB source limit")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Text must be UTF-8 encoded") from exc


def extract_pdf(raw: bytes) -> tuple[str, int]:
    if not raw.startswith(b"%PDF-"):
        raise ValueError("This file is not a valid PDF")
    try:
        reader = PdfReader(BytesIO(raw), strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("Encrypted PDF: unlock it before uploading")
        pages = len(reader.pages)
        if pages < 1 or pages > 250:
            raise ValueError("PDF must contain 1 to 250 pages")
        parts = []
        for number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                # OCR fallback — only attempted if pytesseract + pdf2image are installed
                text = _ocr_page(raw, number)
            if text.strip():
                parts.append(f"# Page {number}\n{text.strip()}\n")
            if sum(len(part.encode("utf-8")) for part in parts) > MAX_EXTRACTED_BYTES:
                raise ValueError("Extracted PDF text exceeds the 2 MB source limit")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("PDF text could not be extracted; paste the contract text instead") from exc
    if not parts:
        raise ValueError(
            "No selectable text was found in this PDF and OCR is unavailable. "
            "Paste the contract text instead, or install pytesseract + pdf2image for OCR support."
        )
    return "\n".join(parts), pages


def _ocr_page(raw: bytes, page_number: int) -> str:
    """Best-effort OCR for one PDF page. Tries PyMuPDF + easyocr, then pdf2image/pytesseract."""
    # --- 1. PyMuPDF pixmap render + easyocr (zero external binaries needed) ---
    try:
        import pymupdf as fitz  # type: ignore
        from PIL import Image  # type: ignore
        doc = fitz.open(stream=raw, filetype="pdf")
        if 1 <= page_number <= len(doc):
            page = doc.load_page(page_number - 1)
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = _easyocr_image(img)
            if text.strip():
                return text
    except Exception:
        pass

    # --- 2. pdf2image + easyocr ---
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        images = convert_from_bytes(raw, first_page=page_number, last_page=page_number, dpi=200)
        if images:
            text = _easyocr_image(images[0])
            if text.strip():
                return text
    except Exception:
        pass

    # --- 3. pytesseract fallback (requires Tesseract binary) ---
    try:
        import pytesseract  # type: ignore
        from pdf2image import convert_from_bytes  # type: ignore
        images = convert_from_bytes(raw, first_page=page_number, last_page=page_number, dpi=200)
        if images:
            return pytesseract.image_to_string(images[0])
    except Exception:
        pass
    return ""


IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "tiff", "tif", "bmp"}


def _easyocr_image(pil_image) -> str:
    """Run easyocr on a PIL image. Returns joined text or empty string."""
    import numpy as np  # type: ignore
    import easyocr  # type: ignore
    arr = np.array(pil_image)
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    results = reader.readtext(arr, detail=0)
    return "\n".join(results)


def ocr_image(raw: bytes, filename: str = "image") -> str:
    """Extract text from an image file (PNG/JPG/WEBP/TIFF) via OCR.

    Tries easyocr first (no Tesseract required), then pytesseract.
    Raises ValueError if both are unavailable or text is too short.
    """
    from PIL import Image  # type: ignore

    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Image exceeds the 12 MB upload limit")

    try:
        pil_image = Image.open(BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise ValueError("Could not open image file — unsupported format?") from exc

    text = ""
    # 1. easyocr
    try:
        text = _easyocr_image(pil_image)
    except ImportError:
        pass
    except Exception:
        pass

    # 2. pytesseract fallback
    if not text.strip():
        try:
            import pytesseract  # type: ignore
            text = pytesseract.image_to_string(pil_image)
        except ImportError:
            pass
        except Exception:
            pass

    if not text.strip():
        raise ValueError(
            "No text could be extracted from this image. "
            "Make sure easyocr is installed (pip install easyocr) "
            "or install Tesseract and pytesseract."
        )
    return text.strip()





def parse_jsonl(raw: bytes) -> tuple[Literal["events", "contract"], list[OperationalEvent] | str, list[tuple[int, str, str]]]:
    source = decode_text(raw)
    events: list[OperationalEvent] = []
    clauses: list[str] = []
    errors: list[tuple[int, str, str]] = []
    mode: Literal["events", "contract"] | None = None
    for number, line in enumerate(source.splitlines(), start=1):
        if number > 500:
            raise ValueError("JSONL upload exceeds 500 records")
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("Record must be a JSON object")
            kind: Literal["events", "contract"]
            if "event_id" in record or "timestamp" in record:
                kind = "events"
            elif isinstance(record.get("text") or record.get("content"), str):
                kind = "contract"
            else:
                raise ValueError("Record needs event_id/timestamp or text/content")
            if mode and kind != mode:
                raise ValueError("Event and contract records cannot be mixed in one file")
            mode = kind
            if kind == "events":
                events.append(OperationalEvent.model_validate(record))
            else:
                text = record.get("text") or record.get("content")
                if not text.strip():
                    raise ValueError("Contract text is empty")
                clauses.append(f"# Record {number}\n{text.strip()}\n")
        except (ValueError, TypeError, ValidationError) as exc:
            errors.append((number, line, type(exc).__name__))
    if mode is None:
        raise ValueError("JSONL has no valid event or contract text records")
    if mode == "events":
        return mode, events, errors
    text = "\n".join(clauses)
    if len(text.encode("utf-8")) > MAX_EXTRACTED_BYTES:
        raise ValueError("Extracted JSONL contract text exceeds the 2 MB source limit")
    return mode, text, errors
