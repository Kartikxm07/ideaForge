"""
Tyr Agent — Adjudication & Action Drafting
==========================================
Tyr is the fifth and final specialist in the ODIN pipeline.

Responsibility: Rule on all verified findings, assign severity, and
draft concrete review actions. Only findings with verified evidence
from Heimdall reach Tyr; Tyr never rules on unverified claims.
"""
from __future__ import annotations

RESPONSIBILITY = "Rule on verified findings and draft review actions"

__all__ = ["RESPONSIBILITY"]
