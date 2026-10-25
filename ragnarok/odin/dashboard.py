"""Read-only, owner-scoped ODIN dashboard projections from persisted state."""
import json
import sqlite3
import re
from calendar import monthrange
from datetime import date
from pathlib import Path

from ..analysis import run_view
from .engine.calc import calculate_harbor_credit, calculate_stratonode_credit
from ..workflow import task_view


def _decoded(value, fallback):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def _source_excerpt(content: str, start: str, end: str) -> str | None:
    first = content.find(start)
    if first < 0:
        return None
    last = content.find(end, first + len(start))
    return content[first:last if last >= 0 else first + 600].strip()


def _sla_scenarios(db: sqlite3.Connection, owner: str, checkpoint: str, events: list[dict]) -> list[dict]:
    """Illustrative credit arithmetic; source and month-end gates prevent guessed totals."""
    rows = db.execute(
        "SELECT document_key,content FROM documents WHERE owner_id=? AND document_key IN ('A1','A2','A3','B1')",
        (owner,),
    ).fetchall()
    sources = {row["document_key"]: row["content"] for row in rows}
    if len(sources) != 4:
        return []
    b1, a1, a2, a3 = (sources[key] for key in ("B1", "A1", "A2", "A3"))
    customer_fee = re.search(r"Monthly Fee:\s*\$([\d,]+\.\d{2})", b1)
    provider_fee = re.search(r"Monthly Fee:\s*\$([\d,]+\.\d{2})", a1)
    b1_quote = _source_excerpt(b1, "§3.3  Service Credits.", "§3.4  Credit Cap.")
    a2_quote = _source_excerpt(a2, "3.1  If the Monthly Uptime Percentage", "3.2  Credit Request Procedure.")
    a3_quote = _source_excerpt(a3, "Section 3.1 of the SLA is deleted", "SECTION 3 — MODIFICATION")
    if not all((customer_fee, provider_fee, b1_quote, a2_quote, a3_quote)):
        return []
    if not all(("99.9%" in b1, "fifteen percent (15%)" in b1_quote,
                "99.5%" in a2, "sixty (60)" in a3_quote, "five percent (5%)" in a3_quote)):
        return []
    customer_monthly = float(customer_fee.group(1).replace(",", ""))
    provider_monthly = float(provider_fee.group(1).replace(",", ""))
    corroborations = [event for event in events if event["channel"] == "email"
                      and "Quillhub" in (event["sender"] or "")
                      and "Harbor Retail" in (event["recipient"] or "")
                      and "Service Disruption" in (event["subject"] or "")]
    incidents: dict[str, list[tuple[int, str, str]]] = {}
    for event in events:
        if event["channel"] != "status_log":
            continue
        body = event["body"]
        duration = re.search(r"Duration:\s*(\d+) minutes", body)
        start = re.search(r"Incident start:\s*(\d{4}-\d{2}-\d{2})", body)
        if not duration or not start or not re.search(
            r"No Scheduled Maintenance|NOT classified as Scheduled Maintenance", body, re.IGNORECASE
        ):
            continue
        minutes = int(duration.group(1))
        matching = next((item for item in corroborations if f"{minutes} minutes" in item["body"]), None)
        if matching is None:
            continue
        month_key = start.group(1)[:7]
        incidents.setdefault(month_key, []).append((minutes, event["event_id"], matching["event_id"]))
    scenarios = []
    for month_key, group in sorted(incidents.items()):
        year, month = map(int, month_key.split("-"))
        if date(year, month, monthrange(year, month)[1]).isoformat() > checkpoint:
            continue
        downtime = sum(item[0] for item in group)
        harbor = calculate_harbor_credit(downtime, month, year, customer_monthly)
        strato = calculate_stratonode_credit(downtime, max(item[0] for item in group), month, year, provider_monthly)
        scenarios.append({
            "month": month_key, "status": "illustrative; claim and recovery not adjudicated",
            "gross_customer_credit": harbor["credit_amount"],
            "potential_provider_credit": strato["credit_amount"],
            "unrecovered_gap": round(harbor["credit_amount"] - strato["credit_amount"], 2),
            "currency": "USD", "downtime_minutes": downtime,
            "customer_uptime_percentage": harbor["uptime_percentage"],
            "provider_uptime_percentage": strato["uptime_percentage"],
            "customer_formula": f"{customer_monthly:.2f} × {harbor['credit_percentage']}%",
            "provider_formula": f"{provider_monthly:.2f} × {strato['total_credit_percentage']}%",
            "gap_formula": "gross customer credit − potential provider credit",
            "events": [{"provider": item[1], "customer": item[2], "minutes": item[0]} for item in group],
            "citations": [
                {"document_key": "B1", "clause_ref": "§3.3", "quote": b1_quote},
                {"document_key": "A2", "clause_ref": "3.1", "quote": a2_quote},
                {"document_key": "A3", "clause_ref": "Section 2", "quote": a3_quote},
            ],
        })
    return scenarios


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
    output = {"checkpoint": checkpoint, "clock": clock, "documents": documents, "clauses": clauses, "events": events,
              "sla_scenarios": _sla_scenarios(db, owner, checkpoint, events)}
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
