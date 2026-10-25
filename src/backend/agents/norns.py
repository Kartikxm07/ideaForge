"""
Norns Agent — Timeline & Deadline Simulation
============================================
The Norns are the third specialist in the ODIN pipeline.

Responsibility: Project cited dates forward by deterministic calendar
arithmetic. Every deadline is anchored to a verbatim clause date;
no estimated or implied deadlines are created.
"""
from __future__ import annotations

RESPONSIBILITY = "Project cited dates by deterministic calendar arithmetic"

__all__ = ["RESPONSIBILITY"]
