"""
Heimdall Agent — Evidence Verification
=======================================
Heimdall is the second specialist in the ODIN pipeline.

Responsibility: Check every claim Thor extracts against the source
document and recorded operational events. A finding only survives if
Heimdall can confirm it with a verbatim quote at the given offset.
"""
from __future__ import annotations

RESPONSIBILITY = "Check claims against source evidence and recorded events"

__all__ = ["RESPONSIBILITY"]
