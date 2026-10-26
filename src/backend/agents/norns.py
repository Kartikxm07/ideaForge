"""
Norns Agent — Timeline & Deterministic Financial Exposure Engine
=================================================================
The Norns are the time-series and financial exposure specialists in the ODIN pipeline.
Calculates worst-case dollar exposure from payments ledgers and contract penalty formulas.
"""
from __future__ import annotations
from ragnarok.norns_finance import (
    compute_exposure,
    parse_ledger,
    parse_relative_days,
    TimelineMilestone,
)

RESPONSIBILITY = "Project cited dates and compute worst-case financial dollar exposure"

__all__ = [
    "RESPONSIBILITY",
    "compute_exposure",
    "parse_ledger",
    "parse_relative_days",
    "TimelineMilestone",
]
