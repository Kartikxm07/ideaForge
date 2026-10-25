"""Event Stream Parser with Bad-Line Quarantine.
Parses operational JSONL event drops. Any malformed record is safely quarantined,
allowing the rest of the stream to import without interruption.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from ...store import now
from ..models import OperationalEvent


class EventParser:
    """Safe parser for JSONL event streams with bad-line quarantine."""

    def __init__(self, db: sqlite3.Connection, owner_id: str):
        self.db = db
        self.owner_id = owner_id

    def parse_file(self, jsonl_path: Path) -> dict[str, Any]:
        """Read a JSONL file, store valid events, and quarantine invalid lines."""
        if not jsonl_path.exists():
            return {"imported": 0, "errors": 0, "error_details": ["File not found"]}

        imported_count = 0
        error_count = 0
        error_details = []
        current_time = now()

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, start=1):
                clean_line = raw_line.strip()
                if not clean_line:
                    continue  # skip blank lines

                try:
                    data = json.loads(clean_line)
                    if not isinstance(data, dict):
                        raise ValueError("Line is not a valid JSON object")

                    event_id = data.get("event_id")
                    timestamp = data.get("timestamp")
                    if not event_id or not timestamp:
                        raise ValueError("Missing required fields: event_id or timestamp")

                    # Insert into odin_events
                    self.db.execute(
                        """
                        INSERT OR REPLACE INTO odin_events(event_id, owner_id, timestamp, channel, sender, recipient, subject, body, raw_json, created_at)
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_id,
                            self.owner_id,
                            timestamp,
                            data.get("channel"),
                            data.get("from"),
                            data.get("to"),
                            data.get("subject"),
                            data.get("body", ""),
                            clean_line,
                            current_time,
                        ),
                    )
                    imported_count += 1

                except Exception as exc:
                    error_count += 1
                    error_msg = str(exc)
                    line_sha = hashlib.sha256(clean_line.encode("utf-8")).hexdigest()
                    error_id = f"err-{line_no}-{line_sha[:10]}"

                    # Quarantine in odin_parse_errors
                    self.db.execute(
                        """
                        INSERT OR REPLACE INTO odin_parse_errors(error_id, owner_id, source, raw_content, error_message, created_at)
                        VALUES(?, ?, ?, ?, ?, ?)
                        """,
                        (
                            error_id,
                            self.owner_id,
                            f"{jsonl_path.name}:{line_no}",
                            clean_line[:1000],
                            error_msg,
                            current_time,
                        ),
                    )

                    # Also record in existing event_import_errors table for backward compatibility
                    self.db.execute(
                        """
                        INSERT OR IGNORE INTO event_import_errors(id, owner_id, source_file, line_number, line_sha256, error_type, recorded_at)
                        VALUES(?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            error_id,
                            self.owner_id,
                            jsonl_path.name,
                            line_no,
                            line_sha,
                            type(exc).__name__,
                            current_time,
                        ),
                    )

                    error_details.append({
                        "line": line_no,
                        "raw": clean_line[:80],
                        "error": error_msg,
                    })

        return {
            "file": str(jsonl_path),
            "imported": imported_count,
            "errors": error_count,
            "error_details": error_details,
        }
