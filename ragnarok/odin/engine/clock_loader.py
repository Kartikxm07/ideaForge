"""Clock Loader & Simulated Checkpoint Engine.
Loads clock.json and filters events by simulation checkpoint.
"""
from datetime import datetime
import json
from pathlib import Path
from typing import Optional, Union
from ..models import ClockSpec


class ClockLoader:
    """Manages the simulated temporal clock and checkpoint progression."""

    def __init__(self, clock_file_path: Union[Path, str]):
        self.path = Path(clock_file_path)
        self.spec: Optional[ClockSpec] = None
        self.load()

    def load(self) -> ClockSpec:
        """Load and parse clock.json."""
        if not self.path.exists():
            raise FileNotFoundError(f"Clock file not found at {self.path}")

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.spec = ClockSpec(
            start_date=raw.get("start_date", "2027-01-15"),
            checkpoints=raw.get("checkpoints", []),
        )
        return self.spec

    @property
    def start_date(self) -> str:
        return self.spec.start_date if self.spec else "2027-01-15"

    @property
    def checkpoints(self) -> list[str]:
        return self.spec.checkpoints if self.spec else []

    def is_event_prior_to_checkpoint(self, event_timestamp: str, checkpoint_date: str) -> bool:
        """Check if an ISO timestamp is at or before the end of the checkpoint date (23:59:59Z)."""
        ev_date = event_timestamp.split("T")[0]
        return ev_date <= checkpoint_date
