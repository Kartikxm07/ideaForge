"""Document Ingestion & Clause Chunking.
Splits contracts into stable clause IDs and records parse warnings (e.g. missing exhibits in B2).
Preserves verbatim character spans.
"""
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Optional
from ..models import ClauseItem, DocumentMetadata


class DocumentIngestor:
    """Ingests contract text files, indexes sections and clauses, and flags ambiguities."""

    def __init__(self, db: sqlite3.Connection, owner_id: str):
        self.db = db
        self.owner_id = owner_id

    def ingest_document(self, doc_id: str, path: Path, title: str) -> DocumentMetadata:
        """Parse a single contract file, split into clauses, and record in database."""
        raw_text = path.read_text(encoding="utf-8")
        warnings: list[str] = []
        status = "ok"

        # Check for incomplete markers (e.g. B2 missing exhibits)
        if "The document appears to be incomplete" in raw_text or "not included in this copy" in raw_text:
            status = "incomplete"
            warnings.append("Document appears incomplete: exhibits missing from source file.")

        clauses = self._extract_clauses(doc_id, raw_text)

        # Store in odin_documents
        from ...store import now
        current_time = now()
        self.db.execute(
            """
            INSERT OR REPLACE INTO odin_documents(doc_id, owner_id, path, title, status, parse_warnings, clause_count, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                self.owner_id,
                str(path),
                title,
                status,
                json.dumps(warnings),
                len(clauses),
                current_time,
                current_time,
            ),
        )

        # Remove existing clauses for this doc
        self.db.execute(
            "DELETE FROM odin_clauses WHERE doc_id = ? AND owner_id = ?",
            (doc_id, self.owner_id),
        )

        # Insert clauses
        for c in clauses:
            self.db.execute(
                """
                INSERT OR REPLACE INTO odin_clauses(clause_id, doc_id, owner_id, section_ref, heading, body, char_offset_start, char_offset_end, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c.clause_id,
                    c.doc_id,
                    self.owner_id,
                    c.section_ref,
                    c.heading,
                    c.body,
                    c.char_offset_start,
                    c.char_offset_end,
                    current_time,
                ),
            )

        return DocumentMetadata(
            doc_id=doc_id,
            path=str(path),
            title=title,
            status=status,
            parse_warnings=warnings,
            clause_count=len(clauses),
        )

    def _extract_clauses(self, doc_id: str, text: str) -> list[ClauseItem]:
        """Split text into structured clauses with stable IDs."""
        clauses: list[ClauseItem] = []

        # Heading regex matching common section indicators
        heading_pattern = re.compile(
            r"(^(?:SECTION\s+\d+|Section\s+[A-Z0-9]+|§\s*\d+(?:\.\d+)*|ARTICLE\s+\d+|[A-Z0-9\.\s]{3,40}(?:—|-)\s+[A-Za-z\s]+)\b.*$)",
            re.MULTILINE,
        )

        matches = list(heading_pattern.finditer(text))

        if not matches:
            # Whole document as single clause
            clauses.append(
                ClauseItem(
                    clause_id=f"{doc_id}-Main",
                    doc_id=doc_id,
                    section_ref="Main",
                    heading=doc_id,
                    body=text.strip(),
                    char_offset_start=0,
                    char_offset_end=len(text),
                )
            )
            return clauses

        # Handle preamble if any before first section
        first_start = matches[0].start()
        if first_start > 50:
            preamble = text[:first_start].strip()
            if preamble:
                clauses.append(
                    ClauseItem(
                        clause_id=f"{doc_id}-Preamble",
                        doc_id=doc_id,
                        section_ref="Preamble",
                        heading="Preamble",
                        body=preamble,
                        char_offset_start=0,
                        char_offset_end=first_start,
                    )
                )

        seen_counts: dict[str, int] = {}
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            heading_line = match.group(0).strip()
            body_block = text[start:end].strip()

            # Clean clause reference tag
            ref_match = re.search(r"(?:SECTION\s+(\d+)|Section\s+([A-Z0-9]+)|§\s*(\d+(?:\.\d+)*))", heading_line, re.IGNORECASE)
            if ref_match:
                ref_num = next(g for g in ref_match.groups() if g is not None)
                section_ref = f"§{ref_num}"
            else:
                clean_heading = re.sub(r"[^A-Za-z0-9_-]", "_", heading_line[:20]).strip("_")
                section_ref = clean_heading if clean_heading else f"Sec_{i+1}"

            seen_counts[section_ref] = seen_counts.get(section_ref, 0) + 1
            idx_suffix = f"_{seen_counts[section_ref]}" if seen_counts[section_ref] > 1 else ""
            clause_id = f"{doc_id}-{section_ref}{idx_suffix}".replace(" ", "_")

            clauses.append(
                ClauseItem(
                    clause_id=clause_id,
                    doc_id=doc_id,
                    section_ref=section_ref,
                    heading=heading_line,
                    body=body_block,
                    char_offset_start=start,
                    char_offset_end=end,
                )
            )

        return clauses

    def ingest_bundle(self, bundle_dir: Path) -> list[DocumentMetadata]:
        """Ingest all contracts described in bundle/manifest.json."""
        manifest_path = bundle_dir / "manifest.json"
        if not manifest_path.exists():
            manifest_path = bundle_dir / "bundle" / "manifest.json"

        results = []
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            base_dir = manifest_path.parent
            for file_entry in manifest.get("files", []):
                rel_path = file_entry.get("path", "")
                if rel_path.startswith("contracts/") and rel_path.endswith(".txt"):
                    file_path = base_dir / rel_path
                    if file_path.exists():
                        doc_id = Path(rel_path).stem
                        title = file_entry.get("title", doc_id)
                        meta = self.ingest_document(doc_id, file_path, title)
                        results.append(meta)
        return results
