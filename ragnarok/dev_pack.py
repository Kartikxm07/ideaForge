"""Import the supplied ODIN development bundle into an isolated SQLite owner."""
from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from .documents import upsert_document
from .operational_events import import_event_records
from .store import Store, now
from .upload_formats import parse_jsonl


def _save_input(store: Store, owner: str, kind: str, source: str, data: dict) -> None:
    key = hashlib.sha256(f"{owner}\0{kind}\0{source}".encode()).hexdigest()
    with store.connect() as db:
        db.execute(
            "INSERT INTO web_records(id,owner_id,kind,data,created_at,updated_at) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at",
            (key, owner, kind, json.dumps({"source": source, **data}, ensure_ascii=False), now(), now()),
        )


def import_dev_pack(store: Store, owner: str, pack: Path) -> dict:
    pack = pack.resolve()
    bundle = pack / "bundle"
    if not bundle.is_dir():
        raise ValueError("Expected an odin_dev_pack directory with a bundle folder")
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    titles = {item["path"]: item["title"] for item in manifest["files"]}
    keys = []
    for path in sorted((bundle / "contracts").glob("*.txt")):
        relative = path.relative_to(bundle).as_posix()
        key = path.stem
        upsert_document(store, owner, key, titles.get(relative, key),
                        path.read_text(encoding="utf-8-sig"), f"dev-pack:{relative}")
        keys.append(key)
    if not keys:
        raise ValueError("The bundle has no canonical contract text files")

    context = (bundle / "company" / "context.txt").read_text(encoding="utf-8-sig")
    _save_input(store, owner, "agent-context", "company/context.txt", {"content": context})

    counts = {}
    for filename, kind, required in (
        ("payments_ledger.csv", "agent-ledger-row", {"date", "from", "to", "amount", "reference", "status"}),
        ("holidays.csv", "agent-holiday", {"date", "name", "observed_by"}),
    ):
        with (bundle / "data" / filename).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"Unexpected columns in {filename}")
            rows = list(reader)
        for number, row in enumerate(rows, 2):
            date.fromisoformat(row["date"])
            if "amount" in row:
                Decimal(row["amount"])
            _save_input(store, owner, kind, f"data/{filename}:{number}", row)
        counts[filename] = len(rows)

    event_counts = {}
    for path in sorted((bundle / "events").glob("*.jsonl")):
        mode, parsed, errors = parse_jsonl(path.read_bytes())
        if mode != "events":
            raise ValueError(f"Expected event records in {path.name}")
        event_counts[path.name] = import_event_records(store, owner, path.name, parsed, errors)

    clock = json.loads((pack / "clock.json").read_text(encoding="utf-8"))
    checkpoints = [date.fromisoformat(value).isoformat() for value in clock["checkpoints"]]
    if not checkpoints or checkpoints != sorted(set(checkpoints)):
        raise ValueError("Clock checkpoints must be distinct and chronological")
    return {"document_keys": keys, "checkpoints": checkpoints,
            "event_drops": event_counts, "ledger_rows": counts["payments_ledger.csv"],
            "holiday_rows": counts["holidays.csv"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the fictional ODIN development bundle")
    parser.add_argument("pack", type=Path)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--owner", required=True)
    args = parser.parse_args()
    store = Store(args.db)
    store.migrate()
    print(json.dumps(import_dev_pack(store, args.owner, args.pack), indent=2))


if __name__ == "__main__":
    main()
