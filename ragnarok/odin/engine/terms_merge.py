"""Terms Merge Engine.
Deterministically resolves amendments (e.g. A3 over A1/A2, B2 over B1) and
incorporated master standard terms (STD), preserving both original and superseding citations.
"""
import json
import sqlite3
from typing import Any, Optional
import uuid
from ...store import now
from ..models import EffectiveTerm, Citation


class TermsMergeEngine:
    """Applies amendments and master terms to produce effective terms."""

    def __init__(self, db: sqlite3.Connection, owner_id: str):
        self.db = db
        self.owner_id = owner_id

    def merge_terms(self, base_terms: list[dict[str, Any]], amendments: list[dict[str, Any]]) -> list[EffectiveTerm]:
        """Merge base terms with amendments, recording overrides and citations."""
        effective_map: dict[str, EffectiveTerm] = {}
        current_time = now()

        # 1. Process base terms
        for item in base_terms:
            doc_id = item["doc_id"]
            term_key = item["term_key"]
            citations = [Citation(**c) for c in item.get("citations", [])]
            t_id = f"term-{uuid.uuid4().hex[:10]}"
            effective_map[f"{doc_id}:{term_key}"] = EffectiveTerm(
                term_id=t_id,
                doc_id=doc_id,
                term_key=term_key,
                value=str(item["value"]),
                derived_from=citations,
                superseded_by=None,
                note=item.get("note"),
            )

        # 2. Apply amendments
        for amd in amendments:
            target_doc = amd["target_doc_id"]
            term_key = amd["term_key"]
            amd_doc = amd["amd_doc_id"]
            new_value = str(amd["new_value"])
            amd_citations = [Citation(**c) for c in amd.get("citations", [])]

            key = f"{target_doc}:{term_key}"
            if key in effective_map:
                existing = effective_map[key]
                combined_citations = existing.derived_from + amd_citations
                t_id = f"term-{uuid.uuid4().hex[:10]}"
                effective_map[key] = EffectiveTerm(
                    term_id=t_id,
                    doc_id=target_doc,
                    term_key=term_key,
                    value=new_value,
                    derived_from=combined_citations,
                    superseded_by=amd_doc,
                    note=f"Overridden by {amd_doc}: {amd.get('note', '')}",
                )
            else:
                t_id = f"term-{uuid.uuid4().hex[:10]}"
                effective_map[key] = EffectiveTerm(
                    term_id=t_id,
                    doc_id=target_doc,
                    term_key=term_key,
                    value=new_value,
                    derived_from=amd_citations,
                    superseded_by=amd_doc,
                    note=f"Introduced by amendment {amd_doc}",
                )

        # 3. Persist into odin_effective_terms
        results = list(effective_map.values())
        for term in results:
            citations_json = json.dumps([c.model_dump() for c in term.derived_from])
            self.db.execute(
                """
                INSERT OR REPLACE INTO odin_effective_terms(term_id, owner_id, doc_id, term_key, value, derived_from, superseded_by, note, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    term.term_id,
                    self.owner_id,
                    term.doc_id,
                    term.term_key,
                    term.value,
                    citations_json,
                    term.superseded_by,
                    term.note,
                    current_time,
                ),
            )

        return results
