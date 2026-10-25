"""Bounded, evidence-gated ODIN specialist workflow over stored contracts.

Every stage is persisted independently. A failure marks the run incomplete and
keeps earlier verified work available to the dashboard.
"""
from __future__ import annotations

from datetime import date, datetime
import json
import re
from uuid import uuid4

from .documents import HEADING, verify_citation
from .model import _parse_json_response
from .store import Store, now

AGENTS = {
    "Thor": "Extract exact contract terms and citations",
    "Heimdall": "Check claims against source evidence and recorded events",
    "Norns": "Project cited dates by deterministic calendar arithmetic",
    "Loki": "Challenge terms and identify evidence-backed risks",
    "Tyr": "Rule on verified findings and draft review actions",
}

THOR_CHUNK_CHARS = 20_000


def contract_warning(content: str) -> str | None:
    """Catch obvious accidental uploads before spending model tokens."""
    sample = content[:50_000]
    if re.search(r"(?im)^\s*(?:nping:|nmap\b|usage:\s*nping|\S+@\S+:[^\n]*\$\s)", sample):
        return "This file appears to be terminal or network scan output, not a contract. Upload an agreement or terms document."
    legal_markers = ("agreement", "contract", "shall", "effective date", "governing law", "counterparty", "renewal", "indemnity", "notice")
    found = sum(bool(re.search(r"\b" + re.escape(term) + r"\b", sample, re.IGNORECASE)) for term in legal_markers)
    if not HEADING.search(sample) and found < 2:
        return "No recognizable contract clauses or legal terms were found. Upload an agreement or terms document."
    return None


def thor_chunks(content: str, limit: int = THOR_CHUNK_CHARS) -> list[str]:
    """Split a full contract at line boundaries, carrying the active clause heading."""
    chunks: list[str] = []
    current = ""
    heading = "Source document"
    for line in content.splitlines(keepends=True):
        match = HEADING.match(line)
        if match:
            heading = match.group(1).strip()[:100]
        while line:
            room = limit - len(current)
            if room <= 0:
                chunks.append(current)
                current = ""
                room = limit
            if current and len(line) > room and len(line) <= limit - min(len(heading) + 1, 200):
                chunks.append(current)
                current = "" if match else (heading + "\n" if heading != "Source document" else "")
                continue
            if len(line) <= room:
                current += line
                break
            cut = line.rfind("\n", 0, room + 1)
            if cut < max(1, room // 2):
                cut = room
            else:
                cut += 1
            current += line[:cut]
            line = line[cut:]
            chunks.append(current)
            current = ""
            if line and heading != "Source document" and not line.startswith(heading):
                current = heading + "\n"
    if current:
        chunks.append(current)
    return chunks


def _save(db, owner: str, kind: str, data: dict, key: str | None = None) -> dict:
    key = key or str(uuid4())
    db.execute(
        "INSERT INTO web_records(id,owner_id,kind,data,created_at,updated_at) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at",
        (key, owner, kind, json.dumps(data, ensure_ascii=False), now(), now()),
    )
    return {"id": key, **data}


def _list(db, owner: str, kind: str, run_id: str | None = None) -> list[dict]:
    rows = db.execute("SELECT id,data,created_at FROM web_records WHERE owner_id=? AND kind=? ORDER BY created_at", (owner, kind))
    items = [{"id": r["id"], "created_at": r["created_at"], **json.loads(r["data"])} for r in rows]
    return [x for x in items if x.get("run_id") == run_id] if run_id else items


def start_run(store: Store, owner: str, keys: list[str], checkpoints: list[str] | None = None) -> dict:
    if not keys or len(keys) > 20 or len(set(keys)) != len(keys):
        raise ValueError("Choose 1 to 20 distinct contracts")
    checkpoints = checkpoints or [date.today().isoformat()]
    if len(checkpoints) > 12 or checkpoints != sorted(set(checkpoints)):
        raise ValueError("Choose 1 to 12 distinct checkpoints in chronological order")
    try:
        checkpoints = [date.fromisoformat(value).isoformat() for value in checkpoints]
    except (TypeError, ValueError) as exc:
        raise ValueError("Checkpoints must be ISO dates") from exc
    with store.connect() as db:
        docs = db.execute("SELECT document_key,content_sha256,content FROM documents WHERE owner_id=?", (owner,)).fetchall()
        hashes = {r["document_key"]: r["content_sha256"] for r in docs}
        if any(k not in hashes for k in keys):
            raise ValueError("All selected contracts must exist in this organization")
        for doc in docs:
            if doc["document_key"] in keys:
                warning = contract_warning(doc["content"])
                if warning:
                    raise ValueError(f"{doc['document_key']}: {warning}")
        return _save(db, owner, "agent-run", {"status": "QUEUED", "document_keys": keys, "hashes": {k: hashes[k] for k in keys}, "checkpoints": checkpoints, "error": None, "started_at": now(), "finished_at": None})


def run_view(store: Store, owner: str, run_id: str) -> dict | None:
    with store.connect() as db:
        run = next((r for r in _list(db, owner, "agent-run") if r["id"] == run_id), None)
        if not run:
            return None
        return {**run, "extractions": _list(db, owner, "agent-extraction", run_id),
                "timeline": _list(db, owner, "agent-timeline", run_id),
                "scenarios": _list(db, owner, "agent-scenario", run_id),
                "findings": _list(db, owner, "agent-finding", run_id),
                "verifications": _list(db, owner, "agent-verification", run_id),
                "rulings": _list(db, owner, "agent-ruling", run_id),
                "email_drafts": _list(db, owner, "agent-email-draft", run_id),
                "messages": _list(db, owner, "agent-message", run_id)}


def latest_view(store: Store, owner: str) -> dict | None:
    with store.connect() as db:
        rows = _list(db, owner, "agent-run")
    return run_view(store, owner, rows[-1]["id"]) if rows else None


def _message(store: Store, owner: str, run_id: str, sender: str, recipient: str, message: str, payload_ref: str | None = None):
    with store.connect() as db:
        _save(db, owner, "agent-message", {"run_id": run_id, "from": sender, "to": recipient, "message": message, "payload_ref": payload_ref, "at": now()})


def _set_status(store: Store, owner: str, run_id: str, status: str, error: str | None = None):
    with store.connect() as db:
        row = db.execute("SELECT data FROM web_records WHERE id=? AND owner_id=? AND kind='agent-run'", (run_id, owner)).fetchone()
        if not row:
            return
        state = json.loads(row["data"])
        state.update(status=status, error=error, finished_at=now() if status in ("COMPLETE", "INCOMPLETE") else None)
        _save(db, owner, "agent-run", state, run_id)


def _json_call(model, prompt: str, limit: int = 2500) -> dict:
    for attempt in range(2):
        raw = model._call(prompt + ("\nReturn valid JSON only." if attempt else ""), model.settings.model_heavy, limit)
        try:
            value = _parse_json_response(raw)
            if isinstance(value, dict):
                return value
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    raise ValueError("Model did not return a valid JSON object")


def _verified(db, owner: str, citations: list) -> list[dict]:
    accepted = []
    for item in citations[:4]:
        if not isinstance(item, dict):
            continue
        key, ref, quote = (item.get(k) for k in ("document_key", "clause_ref", "quote"))
        if not all(isinstance(v, str) and v for v in (key, ref, quote)):
            continue
        try:
            result = verify_citation(db, owner, key, ref, quote)
        except (ValueError, LookupError):
            continue
        if result["verified"]:
            accepted.append({"document_key": key, "clause_ref": ref, "quote": quote, "offset": result["offset"], "content_sha256": result["content_sha256"]})
    return accepted


def _explicit_dates(quote: str) -> list[str]:
    """Parse dates printed in a cited quote, without estimating implied deadlines."""
    found: set[str] = set()
    patterns = [
        (r"\b20\d\d-[01]\d-[0-3]\d\b", "%Y-%m-%d"),
        (r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d\d\b", "%B %d, %Y"),
        (r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d\d\b", "%d %B %Y"),
    ]
    for pattern, format_string in patterns:
        for match in re.finditer(pattern, quote, re.IGNORECASE):
            try:
                value = match.group().strip()
                if format_string == "%B %d, %Y":
                    value = re.sub(r"\s+", " ", value).replace(",", "")
                    parsed = datetime.strptime(value, "%B %d %Y").date()
                else:
                    parsed = datetime.strptime(value, format_string).date()
                found.add(parsed.isoformat())
            except ValueError:
                continue
    return sorted(found)


def execute_run(store: Store, owner: str, run_id: str, model) -> None:
    """Run or resume the checkpointed ODIN graph behind the existing API."""
    from .agent_graph import execute_graph

    execute_graph(store, owner, run_id, model)
