"""
Thor Agent — Contract Term Extraction & Bounding-Box Grounding
==============================================================
Thor is the first specialist in the ODIN pipeline.
Extracts verbatim terms, maps PyMuPDF bounding rects, and rejects fabricated quotes.
"""
from __future__ import annotations
from ragnarok.agents import thor_chunks, THOR_CHUNK_CHARS
from thor_agent.thor import ThorAgent, ThorExtractor, ClauseChunk, ClauseChunker, ExtractedFact
from thor_agent.storage import ChunkStorage
from thor_agent.ocr_pdf import PDFProcessor

RESPONSIBILITY = "Extract exact contract terms and citations anchored to bounding rects"

__all__ = [
    "RESPONSIBILITY",
    "ThorAgent",
    "ThorExtractor",
    "ClauseChunk",
    "ClauseChunker",
    "ExtractedFact",
    "ChunkStorage",
    "PDFProcessor",
    "thor_chunks",
    "THOR_CHUNK_CHARS",
]
