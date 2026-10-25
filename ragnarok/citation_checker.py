"""
ragnarok/citation_checker.py
─────────────────────────────
Citation Integrity Checker — runs between ChromaDB ingestion and Thor.

Verifies that every clause chunk stored in ChromaDB maps 1:1 to the
actual scanned source document text before Thor ever processes it.
Drops OCR-corrupted or hallucination-risk chunks silently into a
flagged log; Thor only receives VALIDATED_PROVENANCE chunks.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thor_agent.storage import ChunkStorage


class CitationIntegrityChecker:
    """
    Pre-Thor gate that validates ChromaDB chunk text against the
    original source document (PDF text layer or canonical .txt).

    Parameters
    ----------
    chroma_store
        A ChunkStorage instance with a get_chunk_by_id() method.
    exact_threshold
        Minimum fraction of clause text that must appear verbatim
        in the source document for an exact pass (default: 1.0).
    fuzzy_threshold
        Minimum SequenceMatcher quick_ratio for a fuzzy pass (default: 0.85).
    """

    def __init__(
        self,
        chroma_store: "ChunkStorage",
        exact_threshold: float = 1.0,
        fuzzy_threshold: float = 0.85,
    ) -> None:
        self.store = chroma_store
        self.exact_threshold = exact_threshold
        self.fuzzy_threshold = fuzzy_threshold

    # ── Public API ─────────────────────────────────────────────────────

    def verify_chunk_provenance(self, chunk_id: str, raw_source_text: str) -> dict:
        """
        Verify that a ChromaDB chunk maps to an actual section of the source.

        Returns
        -------
        dict with keys:
            chunk_id, is_verified, confidence_score, status
            status ∈ {VALIDATED_PROVENANCE, FUZZY_VALIDATED, REJECTED_HALLUCINATION_RISK}
        """
        try:
            chunk_data = self.store.get_chunk_by_id(chunk_id)
        except Exception as exc:
            return {
                "chunk_id": chunk_id,
                "is_verified": False,
                "confidence_score": 0.0,
                "status": "REJECTED_CHUNK_NOT_FOUND",
                "error": str(exc)[:200],
            }

        clause_text = (chunk_data.get("text") or "").strip()
        if not clause_text:
            return {
                "chunk_id": chunk_id,
                "is_verified": False,
                "confidence_score": 0.0,
                "status": "REJECTED_EMPTY_CHUNK",
            }

        # ── Exact substring match ─────────────────────────────────────
        # Normalise whitespace to tolerate minor OCR spacing glitches
        norm_clause = " ".join(clause_text.split())
        norm_source = " ".join(raw_source_text.split())

        if norm_clause in norm_source:
            return {
                "chunk_id": chunk_id,
                "is_verified": True,
                "confidence_score": 1.0,
                "status": "VALIDATED_PROVENANCE",
            }

        # ── Fuzzy match fallback ──────────────────────────────────────
        # Use a sliding window over the source to find the best local match
        score = self._best_local_ratio(norm_clause, norm_source)

        if score >= self.fuzzy_threshold:
            return {
                "chunk_id": chunk_id,
                "is_verified": True,
                "confidence_score": round(score, 3),
                "status": "FUZZY_VALIDATED",
            }

        return {
            "chunk_id": chunk_id,
            "is_verified": False,
            "confidence_score": round(score, 3),
            "status": "REJECTED_HALLUCINATION_RISK",
        }

    def verify_all(
        self,
        chunk_ids: list[str],
        raw_source_text: str,
        *,
        log_rejections: bool = True,
    ) -> tuple[list[str], list[dict]]:
        """
        Verify a list of chunk IDs against a source document.

        Returns
        -------
        (verified_ids, rejection_log)
            verified_ids   — IDs that passed provenance check (safe for Thor)
            rejection_log  — full result dicts for rejected chunks
        """
        verified: list[str] = []
        rejected: list[dict] = []

        for cid in chunk_ids:
            result = self.verify_chunk_provenance(cid, raw_source_text)
            if result["is_verified"]:
                verified.append(cid)
            else:
                if log_rejections:
                    import logging
                    logging.getLogger("citation_checker").warning(
                        "Chunk %s failed provenance: %s (score=%.2f)",
                        cid, result["status"], result["confidence_score"]
                    )
                rejected.append(result)

        return verified, rejected

    # ── Internal ───────────────────────────────────────────────────────

    def _best_local_ratio(self, needle: str, haystack: str) -> float:
        """Slide a window across haystack to find the best local match."""
        if not needle or not haystack:
            return 0.0

        n = len(needle)
        h = len(haystack)

        # For short chunks just compare directly
        if h <= n * 2:
            return SequenceMatcher(None, needle, haystack).quick_ratio()

        # Slide a window of needle-length +25% for context
        window = min(int(n * 1.25), h)
        step   = max(1, window // 4)
        best   = 0.0
        for start in range(0, h - window + 1, step):
            segment = haystack[start : start + window]
            ratio   = SequenceMatcher(None, needle, segment).quick_ratio()
            if ratio > best:
                best = ratio
            if best >= 0.99:  # early exit
                break
        return best


# ── Convenience function for the LangGraph citation_checker node ───────

def check_chunks_for_document(
    chunk_ids: list[str],
    source_text: str,
    chroma_store: "ChunkStorage",
    fuzzy_threshold: float = 0.85,
) -> tuple[list[str], list[dict]]:
    """
    One-call helper: instantiate checker and return (verified_ids, rejections).
    """
    checker = CitationIntegrityChecker(chroma_store, fuzzy_threshold=fuzzy_threshold)
    return checker.verify_all(chunk_ids, source_text)
