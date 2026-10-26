"""
Heimdall Agent — Evidence Verification & Noise Filter
======================================================
Heimdall is the second specialist and gatekeeper in the ODIN pipeline.
Cross-examines Thor extractions against operational events and verifies chunk provenance.
"""
from __future__ import annotations
from ragnarok.operational_events import OperationalEvent, list_events, import_event_drop
from ragnarok.citation_checker import CitationIntegrityChecker, check_chunks_for_document

RESPONSIBILITY = "Check claims against source evidence and recorded operational events"

__all__ = [
    "RESPONSIBILITY",
    "OperationalEvent",
    "list_events",
    "import_event_drop",
    "CitationIntegrityChecker",
    "check_chunks_for_document",
]
