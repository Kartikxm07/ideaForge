"""Idempotent local event-drop ledger for checkpoint queries."""
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .store import Store, now


class OperationalEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    event_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    timestamp: datetime
    channel: str = Field(min_length=1, max_length=80)
    sender: str = Field(alias="from", min_length=1, max_length=200)
    recipient: str = Field(alias="to", min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=20_000)

    @field_validator("timestamp")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Event timestamp must include a timezone")
        return value.astimezone(timezone.utc)


def _canonical(event: OperationalEvent) -> dict:
    return {
        "event_id": event.event_id,
        "occurred_at": event.timestamp.isoformat(),
        "channel": event.channel,
        "sender": event.sender,
        "recipient": event.recipient,
        "subject": event.subject,
        "body": event.body,
    }


def _insert(db: sqlite3.Connection, owner_id: str, event: OperationalEvent, source: str) -> bool:
    item = _canonical(event)
    digest = sha256(json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    prior = db.execute("SELECT content_sha256 FROM operational_events WHERE owner_id=? AND event_id=?", (owner_id, event.event_id)).fetchone()
    if prior:
        if prior["content_sha256"] != digest:
            raise ValueError(f"Event ID already exists with different content: {event.event_id}")
        return False
    db.execute(
        "INSERT INTO operational_events(id,owner_id,event_id,occurred_at,channel,sender,recipient,subject,body,content_sha256,source,imported_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), owner_id, event.event_id, item["occurred_at"], event.channel, event.sender, event.recipient, event.subject, event.body, digest, source, now()),
    )
    return True


def add_event(store: Store, owner_id: str, event: OperationalEvent, source: str = "api") -> bool:
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        created = _insert(db, owner_id, event, source)
        Store.audit(db, owner_id, "event.create", event.event_id, "created" if created else "duplicate")
        return created


def import_event_records(store: Store, owner_id: str, filename: str, events: list[OperationalEvent], errors: list[tuple[int, str, str]]) -> dict:
    """Persist a browser JSONL drop and quarantine malformed lines atomically."""
    if not events and not errors:
        raise ValueError("JSONL event file is empty")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        created = sum(_insert(db, owner_id, event, f"browser:{filename}") for event in events)
        for line_number, line, error_type in errors:
            db.execute(
                "INSERT OR IGNORE INTO event_import_errors(id,owner_id,source_file,line_number,line_sha256,error_type,recorded_at) VALUES(?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), owner_id, filename, line_number, sha256(line.encode("utf-8")).hexdigest(), error_type, now()),
            )
        Store.audit(db, owner_id, "event.import", filename, f"created:{created};quarantined:{len(errors)}")
        return {"kind": "events", "records": len(events) + len(errors), "created": created, "duplicates": len(events) - created, "quarantined": len(errors)}


def import_event_drop(store: Store, owner_id: str, path: Path) -> dict:
    file = path.resolve(strict=True)
    if file.suffix.lower() != ".jsonl" or file.stat().st_size > 2_000_000:
        raise ValueError("Event drop must be a JSONL file no larger than 2 MB")
    events = []
    errors = []
    with file.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if number > 500 or len(line.encode("utf-8")) > 30_000:
                raise ValueError("Event drop exceeds record or line limit")
            if not line.strip():
                continue
            try:
                events.append(OperationalEvent.model_validate(json.loads(line)))
            except (ValueError, TypeError) as exc:
                errors.append((number, sha256(line.encode("utf-8")).hexdigest(), type(exc).__name__))
    if not events and not errors:
        raise ValueError("Event drop is empty")
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("Duplicate event IDs inside drop")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        created = sum(_insert(db, owner_id, event, f"drop:{file.name}") for event in events)
        for line_number, digest, error_type in errors:
            db.execute(
                "INSERT OR IGNORE INTO event_import_errors(id,owner_id,source_file,line_number,line_sha256,error_type,recorded_at) VALUES(?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), owner_id, file.name, line_number, digest, error_type, now()),
            )
        Store.audit(db, owner_id, "event.import", file.name, f"created:{created};quarantined:{len(errors)}")
        return {"records": len(events) + len(errors), "created": created, "duplicates": len(events) - created, "quarantined": len(errors)}


def list_events(db: sqlite3.Connection, owner_id: str, as_of: date | None, limit: int = 100) -> list[dict]:
    if as_of is None or as_of == date.max:
        rows = db.execute("SELECT * FROM operational_events WHERE owner_id=? ORDER BY occurred_at,event_id LIMIT ?", (owner_id, limit)).fetchall()
    else:
        exclusive = datetime.combine(as_of + timedelta(days=1), time.min, timezone.utc).isoformat()
        rows = db.execute("SELECT * FROM operational_events WHERE owner_id=? AND occurred_at<? ORDER BY occurred_at,event_id LIMIT ?", (owner_id, exclusive, limit)).fetchall()
    return [dict(row) for row in rows]
