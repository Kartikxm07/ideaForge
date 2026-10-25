"""
thor_agent.ocr_pdf
──────────────────
PDF processing and highlight engine for Thor Sub-Agent:
- Extracts text layer from contract twin PDFs.
- Searches verbatim quotes and clause references across PDF pages.
- Calculates exact highlight bounding boxes [x0, y0, x1, y1] via PyMuPDF (fitz).
- Renders high-resolution highlighted page images (PNG/base64) for the live proof viewer.
- Provides OCR fallback for scanned or textless pages.
"""

from __future__ import annotations
import base64
import io
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
    HAVE_PYMUPDF = True
except ImportError:
    fitz = None
    HAVE_PYMUPDF = False


class PDFProcessor:
    def __init__(self, pack_dir: Optional[str] = None):
        self.pack_dir = Path(pack_dir) if pack_dir else None

    def find_twin_pdf(self, txt_path_or_key: str, base_pack_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Given a txt path or key (e.g. 'contracts/B1.txt' or 'B1'), finds the twin '.pdf'.
        """
        p = Path(txt_path_or_key)
        # Check if direct PDF exists
        if p.suffix.lower() == ".pdf" and p.exists():
            return p
        
        # Check stem.pdf alongside the file
        twin = p.with_suffix(".pdf")
        if twin.exists():
            return twin

        # Search inside base_pack_dir / bundle / contracts
        roots = []
        if base_pack_dir:
            roots.extend([
                base_pack_dir / "bundle" / "contracts",
                base_pack_dir / "contracts",
                base_pack_dir,
            ])
        if self.pack_dir:
            roots.extend([
                self.pack_dir / "bundle" / "contracts",
                self.pack_dir / "contracts",
                self.pack_dir,
            ])

        stem = p.stem.replace(".txt", "")
        for root in roots:
            candidate = root / f"{stem}.pdf"
            if candidate.exists():
                return candidate
        return None

    def get_pdf_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Returns page count, dimensions, and text summary."""
        if not HAVE_PYMUPDF or not pdf_path.exists():
            return {"available": False, "page_count": 0, "pages": []}

        doc = fitz.open(str(pdf_path))
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text() or ""
            pages.append({
                "page_num": i + 1,
                "width": float(page.rect.width),
                "height": float(page.rect.height),
                "char_count": len(text),
                "has_text": len(text.strip()) > 0,
            })
        page_count = len(doc)
        doc.close()
        return {
            "available": True,
            "pdf_path": str(pdf_path),
            "page_count": page_count,
            "pages": pages,
        }

    def find_quote_page_and_rects(
        self,
        pdf_path: Path,
        quote: str,
        clause_ref: Optional[str] = None
    ) -> Tuple[int, List[List[float]]]:
        """
        Search for quote (or key phrases within the quote) on PDF pages.
        Returns: (1-indexed page_num, list of [x0, y0, x1, y1] rects).
        """
        if not HAVE_PYMUPDF or not pdf_path.exists() or not quote:
            return (1, [])

        clean_quote = " ".join(quote.strip().split())
        doc = fitz.open(str(pdf_path))

        # 1. Try search by entire quote or first 80 chars
        search_terms = []
        if len(clean_quote) <= 80:
            search_terms.append(clean_quote)
        else:
            search_terms.append(clean_quote[:75].strip())
            search_terms.append(clean_quote[:50].strip())

        # 2. Try search by clause reference (e.g. "§5.2" or "Section 5.2" or "5.2")
        if clause_ref:
            ref_clean = clause_ref.replace("§", "").strip()
            search_terms.append(f"§{ref_clean}")
            search_terms.append(f"Section {ref_clean}")
            search_terms.append(ref_clean)

        # 3. Add distinctive snippet phrases from quote (sentences or 6-word windows)
        words = clean_quote.split()
        if len(words) >= 5:
            search_terms.append(" ".join(words[:6]))
            search_terms.append(" ".join(words[2:8]))

        for term in search_terms:
            if not term or len(term) < 4:
                continue
            for page_idx, page in enumerate(doc):
                rects = page.search_for(term)
                if rects:
                    doc.close()
                    # Convert fitz.Rect to list [x0, y0, x1, y1]
                    serialized = [[round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)] for r in rects]
                    return (page_idx + 1, serialized)

        # Fallback: scan page text for highest word overlap
        best_page = 1
        max_overlap = -1
        quote_words = set(w.lower() for w in words if len(w) > 3)

        for page_idx, page in enumerate(doc):
            page_text = (page.get_text() or "").lower()
            overlap = sum(1 for w in quote_words if w in page_text)
            if overlap > max_overlap:
                max_overlap = overlap
                best_page = page_idx + 1

        doc.close()
        return (best_page, [])

    def render_highlighted_page(
        self,
        pdf_path: Path,
        page_num: int = 1,
        rects: Optional[List[List[float]]] = None,
        quote_to_highlight: Optional[str] = None,
        dpi: int = 96
    ) -> Tuple[bytes, List[List[float]]]:
        """
        Render a PDF page to PNG bytes with visual highlight overlay boxes.
        Returns: (png_bytes, active_rects)
        """
        if not HAVE_PYMUPDF or not pdf_path.exists():
            return (b"", [])

        doc = fitz.open(str(pdf_path))
        page_idx = max(0, min(page_num - 1, len(doc) - 1))
        page = doc[page_idx]

        active_rects = rects or []

        # If rects not passed, try to dynamically search quote on this page
        if not active_rects and quote_to_highlight:
            words = quote_to_highlight.strip().split()
            candidates = []
            if len(words) >= 4:
                candidates.append(" ".join(words[:5]))
            candidates.append(quote_to_highlight[:50].strip())
            for c in candidates:
                if len(c) > 4:
                    found = page.search_for(c)
                    if found:
                        active_rects = [[round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)] for r in found]
                        break

        # Draw highlight boxes on the page
        for r_coords in active_rects:
            if len(r_coords) == 4:
                rect = fitz.Rect(*r_coords)
                # Expand slightly for visibility
                rect.x0 = max(0, rect.x0 - 2)
                rect.y0 = max(0, rect.y0 - 2)
                rect.x1 = rect.x1 + 2
                rect.y1 = rect.y1 + 2
                
                # Draw cyan/amber glowing highlight box
                page.draw_rect(
                    rect,
                    color=(0.0, 0.75, 1.0),      # Cyan border
                    fill=(0.0, 0.85, 1.0),       # Cyan glow fill
                    fill_opacity=0.28,
                    width=2.0
                )

        try:
            pix = page.get_pixmap(dpi=dpi)
            png_bytes = pix.tobytes("png")
        except Exception:
            try:
                pix = page.get_pixmap(dpi=72)
                png_bytes = pix.tobytes("png")
            except Exception:
                png_bytes = b""
        doc.close()
        return (png_bytes, active_rects)

    def render_page_base64(
        self,
        pdf_path: Path,
        page_num: int = 1,
        rects: Optional[List[List[float]]] = None,
        quote_to_highlight: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Helper returning base64 data URL and metadata for frontend embedding.
        """
        png_bytes, used_rects = self.render_highlighted_page(
            pdf_path,
            page_num=page_num,
            rects=rects,
            quote_to_highlight=quote_to_highlight
        )
        if not png_bytes:
            return {"success": False, "image_data": None, "page_num": page_num, "rects": []}

        b64 = base64.b64encode(png_bytes).decode("ascii")
        return {
            "success": True,
            "image_data": f"data:image/png;base64,{b64}",
            "page_num": page_num,
            "rects": used_rects,
        }

    def ocr_page_if_needed(self, pdf_path: Path, page_num: int = 1) -> str:
        """
        OCR fallback: extracts text from text layer or falls back to OCR if empty.
        """
        if not HAVE_PYMUPDF or not pdf_path.exists():
            return ""

        doc = fitz.open(str(pdf_path))
        page_idx = max(0, min(page_num - 1, len(doc) - 1))
        page = doc[page_idx]
        text = page.get_text() or ""
        
        # If page has text, return it
        if text.strip():
            doc.close()
            return text

        # Attempt OCR via PyMuPDF TextPage OCR if available
        try:
            tp = page.get_textpage_ocr(language="eng", dpi=150)
            ocr_text = tp.extractText() or ""
            doc.close()
            return ocr_text
        except Exception:
            doc.close()
            return "[OCR Fallback: Scanned document page - text recognized as raster image]"
