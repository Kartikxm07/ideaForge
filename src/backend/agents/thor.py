"""
Thor Agent — Contract Term Extraction & Citation
================================================
Thor is the first specialist in the ODIN pipeline.

Responsibility: Extract exact contract terms and citations from each
clause chunk. Thor never paraphrases; every claim is bound to a
verbatim quote and a specific clause reference.

The actual implementation lives in ragnarok/agents.py (thor_chunks)
and ragnarok/agent_graph.py (thor stage). This file documents Thor's
contract with the rest of the system and provides a convenient import.
"""
from __future__ import annotations

from ragnarok.agents import thor_chunks, THOR_CHUNK_CHARS

RESPONSIBILITY = "Extract exact contract terms and citations"

__all__ = ["RESPONSIBILITY", "thor_chunks", "THOR_CHUNK_CHARS"]
