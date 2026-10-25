"""Citation Verifier.
Checks that any quoted clause text is a verbatim substring of the canonical source text.
Applies safe whitespace and punctuation normalization to handle line wraps and typographer quotes.
"""
from dataclasses import dataclass
import re
from typing import Optional


@dataclass
class CitationResult:
    verified: bool
    doc_id: str
    clause_ref: str
    quote: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    matched_text: Optional[str] = None
    error: Optional[str] = None


class CitationVerifier:
    """Verifies that quotes match source documents verbatim."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Standardize quotes, dashes, and whitespace for comparison."""
        if not text:
            return ""
        # Normalize typographic quotes and apostrophes
        s = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
        # Normalize en-dash / em-dash to hyphen
        s = s.replace("—", "-").replace("–", "-")
        # Normalize whitespace (newlines, tabs, repeated spaces to single space)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def verify(
        self,
        doc_id: str,
        doc_text: str,
        quote: str,
        clause_ref: str = "",
        clause_text: Optional[str] = None,
    ) -> CitationResult:
        """Verify whether quote is a verbatim substring of doc_text (and optionally clause_text)."""
        if not quote or not quote.strip():
            return CitationResult(
                verified=False,
                doc_id=doc_id,
                clause_ref=clause_ref,
                quote=quote,
                error="Empty or whitespace-only quote",
            )

        # 1. Exact raw substring search
        if quote in doc_text:
            pos = doc_text.index(quote)
            return CitationResult(
                verified=True,
                doc_id=doc_id,
                clause_ref=clause_ref,
                quote=quote,
                char_start=pos,
                char_end=pos + len(quote),
                matched_text=quote,
            )

        # 2. Normalized search
        norm_doc = self.normalize_text(doc_text)
        norm_quote = self.normalize_text(quote)

        if norm_quote in norm_doc:
            pos = norm_doc.index(norm_quote)
            return CitationResult(
                verified=True,
                doc_id=doc_id,
                clause_ref=clause_ref,
                quote=quote,
                char_start=pos,
                char_end=pos + len(norm_quote),
                matched_text=norm_doc[pos : pos + len(norm_quote)],
            )

        # 3. If clause_text is provided, check if it's in clause_text
        if clause_text:
            norm_clause = self.normalize_text(clause_text)
            if norm_quote in norm_clause:
                pos = norm_clause.index(norm_quote)
                return CitationResult(
                    verified=True,
                    doc_id=doc_id,
                    clause_ref=clause_ref,
                    quote=quote,
                    char_start=pos,
                    char_end=pos + len(norm_quote),
                    matched_text=norm_clause[pos : pos + len(norm_quote)],
                )

        return CitationResult(
            verified=False,
            doc_id=doc_id,
            clause_ref=clause_ref,
            quote=quote,
            error=f"Quote not found in document '{doc_id}'",
        )
