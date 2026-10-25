"""Read-only, owner-scoped ODIN dashboard projections from persisted state."""
import json
import sqlite3
from pathlib import Path

from ..analysis import run_view
from ..workflow import task_view


def _decoded(value, fallback):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def overview(db: sqlite3.Connection, owner: str, checkpoint: str) -> dict:
    clock_path = Path(__file__).resolve().parents[2] / "odin_dev_pack" / "clock.json"
    clock = json.loads(clock_path.read_text(encoding="utf-8")) if clock_path.exists() else {"checkpoints": []}
    documents = [dict(row) for row in db.execute(
        "SELECT doc_id,title,status,parse_warnings,clause_count FROM odin_documents "
        "WHERE owner_id=? ORDER BY doc_id", (owner,)
    )]
    for document in documents:
        document["parse_warnings"] = _decoded(document["parse_warnings"], [])
    clauses = [dict(row) for row in db.execute(
        "SELECT clause_id,doc_id,section_ref,heading,body FROM odin_clauses "
        "WHERE owner_id=? ORDER BY doc_id,char_offset_start", (owner,)
    )]
    events = [dict(row) for row in db.execute(
        "SELECT event_id,timestamp,channel,sender,recipient,subject,body FROM odin_events "
        "WHERE owner_id=? AND substr(timestamp,1,10)<=? ORDER BY timestamp,event_id", (owner, checkpoint)
    )]
    tables = {
        "timeline": ("odin_timeline", "date,timeline_id"),
        "exposure": ("odin_exposure", "doc_id,scenario"),
        "findings": ("odin_findings", "created_at,finding_id"),
        "alerts": ("odin_alerts", "due_date,alert_id"),
        "messages": ("odin_messages", "timestamp,msg_id"),
    }
    output = {"checkpoint": checkpoint, "clock": clock, "documents": documents, "clauses": clauses, "events": events}
    for key, (table, ordering) in tables.items():
        output[key] = [dict(row) for row in db.execute(
            f"SELECT * FROM {table} WHERE owner_id=? AND clock_t=? ORDER BY {ordering}",
            (owner, checkpoint),
        )]
    for finding in output["findings"]:
        finding["docs"] = _decoded(finding["docs"], [])
        finding["citations"] = _decoded(finding["citations"], [])
    for exposure in output["exposure"]:
        exposure["breakdown"] = _decoded(exposure["breakdown"], exposure["breakdown"])
    output["actions"] = [dict(row) for row in db.execute(
        "SELECT action_id,finding_id,type,recipient,subject,body,citations,deadline,confidence,"
        "needs_human_approval,status,created_at,updated_at FROM odin_actions WHERE owner_id=? "
        "ORDER BY deadline,action_id", (owner,)
    )]
    for action in output["actions"]:
        action["citations"] = _decoded(action["citations"], [])
    output["workstreams"] = [dict(row) for row in db.execute(
        "SELECT ws_id,run_id,type,doc_ids,status,reason,updated_at FROM odin_workstreams "
        "WHERE owner_id=? ORDER BY type,ws_id", (owner,)
    )]
    output["parse_errors"] = [dict(row) for row in db.execute(
        "SELECT source,error_message,created_at FROM odin_parse_errors WHERE owner_id=? ORDER BY created_at DESC LIMIT 20", (owner,)
    )]
    ids = db.execute("SELECT id FROM analysis_runs WHERE owner_id=? ORDER BY created_at DESC LIMIT 20", (owner,)).fetchall()
    output["analyses"] = [run_view(db, owner, row["id"]) for row in ids]
    ids = db.execute("SELECT id FROM tasks WHERE owner_id=? ORDER BY created_at DESC LIMIT 10", (owner,)).fetchall()
    output["tasks"] = [task_view(db, row["id"], owner) for row in ids]
    return output
