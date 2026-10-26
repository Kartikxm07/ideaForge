"""
Unified Backend Module for RAGNAROK / ODIN.
Consolidates Agents, Core Orchestration, Vector Storage, and APIs into a single namespace.
"""
from src.backend.core import (
    Settings,
    Store,
    OdinState,
    build_graph,
    start_run,
    execute_run,
    run_view,
    latest_view,
    compute_exposure,
    parse_ledger,
    parse_relative_days,
    CitationIntegrityChecker,
    check_chunks_for_document,
    OperationalEvent,
)
from src.backend.agents.thor import ThorAgent, ChunkStorage, PDFProcessor
from src.backend.api import create_app, app

__all__ = [
    "Settings",
    "Store",
    "OdinState",
    "build_graph",
    "start_run",
    "execute_run",
    "run_view",
    "latest_view",
    "compute_exposure",
    "parse_ledger",
    "parse_relative_days",
    "CitationIntegrityChecker",
    "check_chunks_for_document",
    "OperationalEvent",
    "ThorAgent",
    "ChunkStorage",
    "PDFProcessor",
    "create_app",
    "app",
]
