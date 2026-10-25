"""Persisted browser workspace, evidence projections and human review workflows.

No inferred financial amounts or fabricated specialist-agent execution records.
"""
import asyncio
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Literal
from urllib.parse import quote as url_quote
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from .analysis import create_run, run_analysis_once, run_view
from .documents import upsert_document
from .model import ClaudeProvider
from .store import Store, now
from .agents import AGENTS, contract_warning, execute_run, latest_view as latest_agent_view, run_view as agent_run_view, start_run as start_agent_run
from .email_delivery import EmailDeliveryError, send_approved_alert
from .operational_events import OperationalEvent, add_event, import_event_records, list_events
from .upload_formats import MAX_UPLOAD_BYTES, decode_text, extract_pdf, parse_jsonl, safe_document_key


class Upload(BaseModel):
    document_key: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2_000_000)


class Analysis(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    focus: str = Field(min_length=2, max_length=100)
    document_keys: list[str] = Field(min_length=1, max_length=3)
    provider_kind: Literal["anthropic", "deterministic"] = "anthropic"


class Review(BaseModel):
    status: Literal["New", "Acknowledged", "Under Review", "Resolved"]
    severity: Literal["Unrated", "Low", "Medium", "High", "Critical"] = "Unrated"


class Action(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    contract_id: str = Field(min_length=1, max_length=80)
    finding_id: str = Field(min_length=1, max_length=80)
    draft: str = Field(min_length=1, max_length=20000)
    type: Literal["Review memo", "Renewal recommendation", "Termination recommendation", "Breach notice", "Amendment proposal"] = "Review memo"


class ActionEdit(BaseModel):
    draft: str = Field(min_length=1, max_length=20000)
    status: Literal["Draft", "Approved", "Rejected", "Revision requested"] = "Draft"
    version: int = Field(ge=1)


class Obligation(BaseModel):
    contract_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=3, max_length=200)
    due_date: date
    kind: Literal["Payment", "Renewal", "Notice", "Compliance", "Other"]
    quote: str = Field(min_length=1, max_length=1000)
    clause_ref: str = Field(min_length=1, max_length=100)


class Simulation(BaseModel):
    reference_date: date


class Profile(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    organization: str = Field(min_length=2, max_length=120)
    notifications: bool = True


class Member(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    role: Literal["admin", "reviewer", "viewer"]


class AgentRunRequest(BaseModel):
    document_keys: list[str] = Field(min_length=1, max_length=20)
    checkpoints: list[date] | None = Field(default=None, min_length=1, max_length=12)


class EmailDraftApproval(BaseModel):
    recipient: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=20, max_length=10000)


class HumanReviewAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)
    decision: Literal["Approve", "Reject", "Escalate"] = "Approve"


def install_workspace(app, store, settings, owner, session):
    router = APIRouter(prefix="/api/v1/workspace", tags=["ODIN workspace"])

    def records(db, actor, kind):
        return [{**json.loads(r["data"]), "id": r["id"], "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in db.execute("SELECT * FROM web_records WHERE owner_id=? AND kind=? ORDER BY created_at DESC", (actor, kind))]

    def save(db, actor, kind, data, key=None):
        key = key or str(uuid4())
        prior = db.execute("SELECT owner_id,kind FROM web_records WHERE id=?", (key,)).fetchone()
        if prior and (prior["owner_id"] != actor or prior["kind"] != kind):
            raise HTTPException(409, "Record scope conflict")
        db.execute("INSERT INTO web_records VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at", (key, actor, kind, json.dumps(data, default=str), now(), now()))
        Store.audit(db, actor, kind + ".save", key, "allowed")
        return {**data, "id": key}

    def find_record(db, actor, kind, key):
        row = db.execute("SELECT * FROM web_records WHERE owner_id=? AND kind=? AND id=?", (actor, kind, key)).fetchone()
        if not row:
            raise HTTPException(404, "Record not found")
        return {**json.loads(row["data"]), "id": key, "created_at": row["created_at"]}

    def runs(db, actor):
        return [run_view(db, actor, r["id"]) for r in db.execute("SELECT id FROM analysis_runs WHERE owner_id=? ORDER BY created_at DESC", (actor,))]

    def risks(db, actor):
        reviews = {r["finding_id"]: r for r in records(db, actor, "risk-review")}
        return [{**dict(r), "evidence": json.loads(r["evidence_json"]), "severity": reviews.get(r["id"], {}).get("severity", "Unrated"), "review_status": reviews.get(r["id"], {}).get("status", "New")} for r in db.execute("SELECT id,run_id,claim,explanation,evidence_json,status,created_at FROM findings WHERE owner_id=? ORDER BY created_at DESC", (actor,))]

    def contracts(db, actor):
        analysis = runs(db, actor)
        findings = risks(db, actor)
        obligations = records(db, actor, "obligation")
        result = []
        for row in db.execute("SELECT id,document_key,title,content,created_at,updated_at,content_sha256,source FROM documents WHERE owner_id=? ORDER BY updated_at DESC", (actor,)):
            item = dict(row)
            item["warning"] = contract_warning(item.pop("content"))
            related = [r for r in analysis if item["document_key"] in r["document_keys"]]
            levels = [r["severity"] for r in findings if r["status"] != "STALE" and any(e["document_key"] == item["document_key"] for e in r["evidence"])]
            dates = sorted(o["due_date"] for o in obligations if o["contract_id"] == item["document_key"])
            item.update(status=related[0]["status"] if related else "NOT_ANALYZED", last_analyzed=related[0]["updated_at"] if related else None, severity=max(levels, key=lambda x: ["Unrated", "Low", "Medium", "High", "Critical"].index(x)) if levels else "Unrated", next_deadline=dates[0] if dates else None)
            result.append(item)
        return result

    @router.get("/contracts")
    def list_contracts(q: str = "", status: str = "", severity: str = "", page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), sort: Literal["title", "updated_at", "document_key"] = "updated_at", direction: Literal["asc", "desc"] = "desc", actor=Depends(owner)):
        with store.connect() as db:
            items = [c for c in contracts(db, actor) if q.casefold() in (c["title"] + " " + c["document_key"]).casefold() and (not status or c["status"] == status) and (not severity or c["severity"] == severity)]
        items.sort(key=lambda c: c[sort].casefold(), reverse=direction == "desc")
        return {"items": items[(page-1)*page_size:page*page_size], "total": len(items), "page": page, "page_size": page_size}

    @router.post("/upload", status_code=201)
    def upload(body: Upload, actor=Depends(owner)):
        warning = contract_warning(body.content)
        if warning:
            raise HTTPException(422, warning)
        digest = hashlib.sha256(body.content.encode()).hexdigest()
        with store.connect() as db:
            if db.execute("SELECT id FROM documents WHERE owner_id=? AND (document_key=? OR content_sha256=?)", (actor, body.document_key, digest)).fetchone():
                raise HTTPException(409, "This document or identifier already exists. Open the existing contract.")
        try:
            return upsert_document(store, actor, body.document_key, body.title, body.content, "browser:txt")
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @router.post("/upload-file", status_code=201)
    async def upload_file(file: UploadFile = File(...), actor=Depends(owner)):
        filename = (file.filename or "").replace("\\", "/").split("/")[-1]
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in ("txt", "pdf", "jsonl") or len(filename) > 200:
            raise HTTPException(422, "Choose a .txt, .pdf or .jsonl file with a valid name")
        raw = await file.read(MAX_UPLOAD_BYTES + 1)
        await file.close()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File exceeds the 12 MB upload limit")
        if not raw:
            raise HTTPException(422, "File is empty")
        try:
            pages = None
            parse_errors = []
            if extension == "txt":
                content = decode_text(raw)
            elif extension == "pdf":
                content, pages = extract_pdf(raw)
            else:
                kind, parsed, parse_errors = parse_jsonl(raw)
                if kind == "events":
                    try:
                        return import_event_records(store, actor, filename, parsed, parse_errors)
                    except ValueError as exc:
                        raise HTTPException(409, str(exc)) from exc
                content = parsed
            clean_content = re.sub(r"(?m)^# (?:Page|Record) \d+\s*$", "", content)
            warning = contract_warning(clean_content)
            if warning:
                raise ValueError(warning)
            key = safe_document_key(filename)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            with store.connect() as db:
                if db.execute("SELECT id FROM documents WHERE owner_id=? AND (document_key=? OR content_sha256=?)", (actor, key, digest)).fetchone():
                    raise HTTPException(409, "This document or identifier already exists. Open the existing contract.")
            result = upsert_document(store, actor, key, filename, content, f"browser:{extension}")
            with store.connect() as db:
                db.execute("INSERT INTO document_uploads(document_id,owner_id,filename,media_type,raw_sha256,raw,page_count,created_at) VALUES(?,?,?,?,?,?,?,?)", (result["id"], actor, filename, {"txt": "text/plain", "pdf": "application/pdf", "jsonl": "application/x-ndjson"}[extension], hashlib.sha256(raw).hexdigest(), raw, pages, now()))
            return {"kind": "contract", "document_key": key, "title": filename, "pages": pages, "quarantined": len(parse_errors), "error_lines": [number for number, _, _ in parse_errors]}
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("/contracts/{key}/source")
    def download_source(key: str, actor=Depends(owner)):
        with store.connect() as db:
            row = db.execute("SELECT d.title,d.content,u.filename,u.media_type,u.raw FROM documents d LEFT JOIN document_uploads u ON u.document_id=d.id AND u.owner_id=d.owner_id WHERE d.owner_id=? AND d.document_key=?", (actor, key)).fetchone()
        if not row:
            raise HTTPException(404, "Contract not found")
        filename = row["filename"] or row["title"] + ".txt"
        raw = row["raw"] if row["raw"] is not None else row["content"].encode("utf-8")
        return Response(content=raw, media_type=row["media_type"] or "text/plain; charset=utf-8", headers={"Content-Disposition": "inline; filename*=UTF-8''" + url_quote(filename)})

    @router.get("/contracts/{key}")
    def contract(key: str, actor=Depends(owner)):
        with store.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE owner_id=? AND document_key=?", (actor, key)).fetchone()
            if not row:
                raise HTTPException(404, "Contract not found")
            # Clause boundaries retain exact source text and offsets. No invented pages.
            content = row["content"]
            headings = list(re.finditer(r"(?m)^(?:#{1,6}\s+.+|(?:\d+(?:\.\d+)*[.)]?|[A-Z]\d*\.\d+)\s+[^\n]+)$", content))
            clauses = []
            for i, m in enumerate(headings):
                end = headings[i+1].start() if i+1 < len(headings) else len(content)
                clauses.append({"id": str(m.start()), "title": m.group().strip(), "text": content[m.start():end], "offset": m.start()})
            if not clauses:
                clauses = [{"id": "0", "title": "Source document", "text": content, "offset": 0}]
            return {**dict(row), "clauses": clauses, "analyses": [r for r in runs(db, actor) if key in r["document_keys"]], "risks": [r for r in risks(db, actor) if any(e["document_key"] == key for e in r["evidence"])], "obligations": [r for r in records(db, actor, "obligation") if r["contract_id"] == key], "actions": [r for r in records(db, actor, "action") if r["contract_id"] == key]}

    @router.post("/analyses", status_code=201)
    def analyze(body: Analysis, background: BackgroundTasks, request: Request, actor=Depends(owner)):
        try:
            result = create_run(store, actor, body.question, body.focus, body.document_keys, request.headers.get("idempotency-key"), body.provider_kind)
        except LookupError as exc:
            raise HTTPException(404, str(exc))
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        background.add_task(run_analysis_once, store, actor, ClaudeProvider(settings))
        return result

    @router.get("/risks")
    def get_risks(actor=Depends(owner)):
        with store.connect() as db:
            return risks(db, actor)

    @router.patch("/risks/{key}")
    def review_risk(key: str, body: Review, actor=Depends(owner)):
        with store.connect() as db:
            if not db.execute("SELECT id FROM findings WHERE owner_id=? AND id=?", (actor, key)).fetchone():
                raise HTTPException(404, "Finding not found")
            return save(db, actor, "risk-review", {"finding_id": key, **body.model_dump()}, "review:"+key)

    @router.get("/actions")
    def get_actions(actor=Depends(owner)):
        with store.connect() as db:
            return records(db, actor, "action")

    @router.post("/actions", status_code=201)
    def new_action(body: Action, actor=Depends(owner)):
        with store.connect() as db:
            finding = next((r for r in risks(db, actor) if r["id"] == body.finding_id and r["status"] != "STALE"), None)
            if not finding or not any(e["document_key"] == body.contract_id for e in finding["evidence"]):
                raise HTTPException(422, "Select a current finding with evidence for this contract")
            return save(db, actor, "action", {**body.model_dump(), "status": "Draft", "version": 1, "evidence": finding["evidence"], "rationale": finding["explanation"], "history": [{"status": "Draft", "at": now()}]})

    @router.patch("/actions/{key}")
    def edit_action(key: str, body: ActionEdit, actor=Depends(owner)):
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            action = find_record(db, actor, "action", key)
            if action["version"] != body.version:
                raise HTTPException(409, "This draft changed. Reload before saving.")
            if body.status == "Approved":
                finding = db.execute("SELECT status FROM findings WHERE owner_id=? AND id=?", (actor, action["finding_id"])).fetchone()
                if not finding or finding["status"] == "STALE":
                    raise HTTPException(409, "Source evidence changed. Run a new analysis before approval.")
            action.update(draft=body.draft, status=body.status, version=body.version+1)
            action["history"].append({"status": body.status, "at": now()})
            return save(db, actor, "action", action, key)

    @router.get("/timeline")
    def timeline(actor=Depends(owner)):
        with store.connect() as db:
            return {"obligations": records(db, actor, "obligation"), "simulations": records(db, actor, "simulation")[:10]}

    @router.post("/obligations", status_code=201)
    def add_obligation(body: Obligation, actor=Depends(owner)):
        from .documents import verify_citation
        with store.connect() as db:
            try:
                verdict = verify_citation(db, actor, body.contract_id, body.clause_ref, body.quote)
            except (ValueError, LookupError) as exc:
                raise HTTPException(422, str(exc))
            if not verdict["verified"]:
                raise HTTPException(422, "Quote and clause reference must match the source exactly")
            return save(db, actor, "obligation", {**body.model_dump(mode="json"), "basis": "Human-entered deadline; source quote verified", "content_sha256": verdict["content_sha256"]})

    @router.post("/simulate")
    def simulate(body: Simulation, actor=Depends(owner)):
        with store.connect() as db:
            items = records(db, actor, "obligation")
            for item in items:
                source = db.execute("SELECT content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (actor, item["contract_id"])).fetchone()
                item["stale"] = not source or source[0] != item["content_sha256"]
                item["days_remaining"] = (date.fromisoformat(item["due_date"]) - body.reference_date).days
                item["state"] = "Stale source" if item["stale"] else "Overdue" if item["days_remaining"] < 0 else "Due today" if item["days_remaining"] == 0 else "Upcoming"
            items.sort(key=lambda r: r["due_date"])
            return save(db, actor, "simulation", {"reference_date": body.reference_date.isoformat(), "obligations": items, "assumptions": "Calendar-day differences from human-entered, citation-backed deadlines. No payment settlement, holiday adjustment or monetary forecast is inferred.", "exposure": None, "summary": f"{sum(r['state'] == 'Overdue' for r in items)} overdue; {sum(r['state'] == 'Due today' for r in items)} due today; {sum(r['stale'] for r in items)} require source revalidation."})

    @router.get("/agents")
    def agents(actor=Depends(owner)):
        latest = latest_agent_view(store, actor)
        counts = {"Thor": len(latest["extractions"]), "Norns": len(latest["timeline"]), "Loki": len(latest["findings"]), "Heimdall": len(latest["verifications"]), "Tyr": len(latest["rulings"])} if latest else {}
        return [{"name": name, "responsibility": purpose, "state": latest["status"] if latest else "NOT_RUN", "output_count": counts.get(name, 0), "run_id": latest["id"] if latest else None} for name, purpose in AGENTS.items()]

    @router.post("/agents/run", status_code=202)
    def launch_agents(body: AgentRunRequest, background: BackgroundTasks, actor=Depends(owner)):
        try:
            run = start_agent_run(store, actor, body.document_keys,
                                  [point.isoformat() for point in body.checkpoints] if body.checkpoints else None)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        background.add_task(execute_run, store, actor, run["id"], ClaudeProvider(settings))
        return run

    @router.get("/agents/runs/latest")
    def latest_agents(actor=Depends(owner)):
        return latest_agent_view(store, actor) or {"status": "NOT_RUN", "extractions": [], "timeline": [], "scenarios": [], "findings": [], "verifications": [], "rulings": [], "messages": []}

    @router.post("/agents/runs/{run_id}/resume", status_code=202)
    def resume_agents(run_id: str, background: BackgroundTasks, actor=Depends(owner)):
        result = agent_run_view(store, actor, run_id)
        if not result:
            raise HTTPException(404, "Agent run not found")
        if result["status"] != "RUNNING":
            raise HTTPException(409, "Only an interrupted running analysis can be resumed")
        background.add_task(execute_run, store, actor, run_id, ClaudeProvider(settings))
        return {"run_id": run_id, "status": "RESUMING"}

    @router.get("/agents/runs/{run_id}")
    def agent_run(run_id: str, actor=Depends(owner)):
        result = agent_run_view(store, actor, run_id)
        if not result:
            raise HTTPException(404, "Agent run not found")
        return result

    @router.post("/agents/email-drafts/{draft_id}/approve")
    def approve_email_draft(draft_id: str, body: EmailDraftApproval, s=Depends(session)):
        if s["role"] != "admin":
            raise HTTPException(403, "Administrator approval required")
        actor = s["org_id"]
        with store.connect() as db:
            draft = find_record(db, actor, "agent-email-draft", draft_id)
            if draft["status"] not in ("DRAFT", "APPROVED"):
                raise HTTPException(409, "This alert can no longer be edited")
            draft.update(status="APPROVED", recipient=body.recipient.strip().lower(),
                         subject=body.subject.strip(), body=body.body.strip(),
                         approved_by=s["user_id"], approved_at=now())
            draft.pop("id", None)
            draft.pop("created_at", None)
            return save(db, actor, "agent-email-draft", draft, draft_id)

    @router.post("/agents/email-drafts/{draft_id}/send")
    def send_email_draft(draft_id: str, s=Depends(session)):
        if s["role"] != "admin":
            raise HTTPException(403, "Administrator approval required")
        actor = s["org_id"]
        with store.connect() as db:
            draft = find_record(db, actor, "agent-email-draft", draft_id)
        if draft["status"] != "APPROVED":
            raise HTTPException(409, "Approve this alert before sending")
        try:
            provider_id = send_approved_alert(settings, draft)
        except EmailDeliveryError as exc:
            raise HTTPException(503, str(exc)) from exc
        with store.connect() as db:
            current = find_record(db, actor, "agent-email-draft", draft_id)
            if current["status"] == "SENT":
                return current
            current.update(status="SENT", sent_at=now(), provider_id=provider_id)
            current.pop("id", None)
            current.pop("created_at", None)
            return save(db, actor, "agent-email-draft", current, draft_id)

    @router.get("/agents/runs/{run_id}/review-questions")
    def get_review_questions(run_id: str, actor=Depends(owner)):
        """Return one clarifying question per Tyr ruling that needs human input."""
        result = agent_run_view(store, actor, run_id)
        if not result:
            raise HTTPException(404, "Agent run not found")
        with store.connect() as db:
            rulings = [r for r in _list(db, actor, "agent-ruling", run_id) if r.get("outcome") in ("needs_review", "upheld")]
            existing = {r["ruling_id"]: r for r in _list(db, actor, "agent-human-review", run_id)}
        questions = []
        for ruling in rulings:
            review = existing.get(ruling["id"])
            finding_claim = ruling.get("finding_id", "")
            for f in result.get("findings", []):
                if f["id"] == ruling.get("finding_id"):
                    finding_claim = f["claim"]
                    break
            questions.append({
                "id": ruling["id"],
                "run_id": run_id,
                "outcome": ruling["outcome"],
                "finding_claim": finding_claim,
                "rationale": ruling.get("rationale", ""),
                "draft_notice": ruling.get("draft_notice"),
                "citations": ruling.get("citations", []),
                "question": (
                    f"Tyr has flagged this as needing human review:\n\n"
                    f"Finding: {finding_claim}\n"
                    f"Rationale: {ruling.get('rationale', '')}\n\n"
                    f"Do you Approve, Reject, or Escalate this finding? "
                    f"Please provide your reasoning."
                ),
                "answered": review is not None,
                "answer": review.get("answer") if review else None,
                "decision": review.get("decision") if review else None,
                "answered_at": review.get("created_at") if review else None,
            })
        return {"run_id": run_id, "status": result["status"], "questions": questions,
                "pending": sum(1 for q in questions if not q["answered"])}

    def _list(db, actor, kind, run_id):
        return [{**json.loads(r["data"]), "id": r["id"], "created_at": r["created_at"]}
                for r in db.execute(
                    "SELECT * FROM web_records WHERE owner_id=? AND kind=? AND json_extract(data,'$.run_id')=? ORDER BY created_at",
                    (actor, kind, run_id))]

    @router.post("/agents/runs/{run_id}/review-questions/{question_id}/answer", status_code=201)
    def answer_review_question(run_id: str, question_id: str, body: HumanReviewAnswer, s=Depends(session)):
        """Store a human review answer for a Tyr ruling. Any team member can review."""
        actor = s["org_id"]
        result = agent_run_view(store, actor, run_id)
        if not result:
            raise HTTPException(404, "Agent run not found")
        with store.connect() as db:
            rulings = _list(db, actor, "agent-ruling", run_id)
            ruling = next((r for r in rulings if r["id"] == question_id), None)
            if not ruling:
                raise HTTPException(404, "Ruling not found in this run")
            key = f"review:{run_id}:{question_id}"
            return save(db, actor, "agent-human-review", {
                "run_id": run_id,
                "ruling_id": question_id,
                "finding_id": ruling.get("finding_id"),
                "answer": body.answer.strip(),
                "decision": body.decision,
                "reviewer_id": s["user_id"],
                "reviewer_name": s["name"],
                "reviewed_at": now(),
            }, key)

    @router.get("/events")
    def workspace_events(as_of: date | None = None, actor=Depends(owner)):
        with store.connect() as db:
            return list_events(db, actor, as_of, 500)

    @router.post("/events", status_code=201)
    def workspace_add_event(body: OperationalEvent, actor=Depends(owner)):
        try:
            created = add_event(store, actor, body, "browser")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"event_id": body.event_id, "created": created}

    @router.get("/dashboard")
    def dashboard(actor=Depends(owner)):
        with store.connect() as db:
            docs, findings = contracts(db, actor), risks(db, actor)
            obligations, actions = records(db, actor, "obligation"), records(db, actor, "action")
            today = datetime.now(timezone.utc).date()
            deadlines = sorted(obligations, key=lambda o: o["due_date"])
            event_count = db.execute("SELECT COUNT(*) FROM operational_events WHERE owner_id=?", (actor,)).fetchone()[0]
            activity = [dict(r) for r in db.execute("SELECT * FROM audit_events WHERE owner_id=? ORDER BY id DESC LIMIT 15", (actor,))]
            distribution = [{"name": level, "value": sum(d["severity"] == level for d in docs)} for level in ["Critical", "High", "Medium", "Low", "Unrated"]]
            return {"metrics": {"contracts": len(docs), "high_risk": sum(d["severity"] in ["High", "Critical"] for d in docs), "deadlines": sum(0 <= (date.fromisoformat(o["due_date"]) - today).days <= 30 for o in obligations), "actions": sum(a["status"] in ["Draft", "Revision requested"] for a in actions), "events": event_count}, "distribution": distribution, "deadlines": deadlines[:6], "activity": activity, "exposure": [], "exposure_note": "No quantified financial forecast is available from the current analysis engine.", "unrated": sum(d["severity"] == "Unrated" for d in docs)}

    @router.get("/reports")
    def get_reports(actor=Depends(owner)):
        with store.connect() as db:
            return records(db, actor, "report")

    @router.post("/reports", status_code=201)
    def make_report(contract_id: str | None = None, actor=Depends(owner)):
        with store.connect() as db:
            completed = [r for r in runs(db, actor) if r["status"] == "COMPLETED" and (not contract_id or contract_id in r["document_keys"])]
            if not completed:
                raise HTTPException(409, "Complete an analysis before generating a report")
            return save(db, actor, "report", {"title": f"{contract_id or 'Company'} risk report", "contract_id": contract_id, "analyses": completed, "obligations": [o for o in records(db, actor, "obligation") if not contract_id or o["contract_id"] == contract_id], "actions": [a for a in records(db, actor, "action") if not contract_id or a["contract_id"] == contract_id], "uncertainty": "Evidence-checked hypotheses are not proven breaches. Severity is assigned by reviewers. Financial exposure is unquantified.", "generated_at": now()})

    @router.get("/reports/{key}")
    def report(key: str, actor=Depends(owner)):
        with store.connect() as db:
            return find_record(db, actor, "report", key)

    @router.get("/graph")
    def graph(actor=Depends(owner)):
        with store.connect() as db:
            nodes, edges = {}, []
            for d in contracts(db, actor):
                nodes[d["document_key"]] = {"id": d["document_key"], "label": d["title"], "kind": "contract", "href": "/contracts/" + d["document_key"]}
            latest = latest_agent_view(store, actor)
            if latest:
                for term in latest["extractions"]:
                    key = term["document_key"] + ":" + term["citation"]["clause_ref"]
                    nodes[key] = {"id": key, "label": term["citation"]["clause_ref"], "kind": "clause", "href": "/contracts/" + term["document_key"]}
                    edges.append({"id": key + ":contract", "source": key, "target": term["document_key"], "label": "Belongs to"})
                    if "part" in term["field"].casefold():
                        party = "party:" + term["value"][:100]
                        nodes[party] = {"id": party, "label": term["value"][:100], "kind": "party"}
                        edges.append({"id": key + ":party", "source": key, "target": party, "label": "Names party"})
                    if "incorporat" in term["citation"]["quote"].casefold():
                        for other in contracts(db, actor):
                            target = other["document_key"]
                            if target != term["document_key"] and re.search(r"\b" + re.escape(target) + r"\b", term["citation"]["quote"]):
                                edges.append({"id": key + ":incorporates:" + target, "source": term["document_key"], "target": target, "label": "Incorporates"})
                for f in latest["findings"]:
                    nodes[f["id"]] = {"id": f["id"], "label": f["claim"], "kind": "risk", "severity": f["severity"]}
                    for cite in f["citations"]:
                        key = cite["document_key"] + ":" + cite["clause_ref"]
                        if key in nodes:
                            edges.append({"id": f["id"] + ":" + key, "source": f["id"], "target": key, "label": "Cites"})
                    cited_docs = sorted({cite["document_key"] for cite in f["citations"]})
                    if len(cited_docs) > 1 and any(word in f["claim"].casefold() for word in ("conflict", "inconsistent", "asymmetr", "mismatch")):
                        for target in cited_docs[1:]:
                            edges.append({"id": f["id"] + ":conflict:" + target, "source": cited_docs[0], "target": target, "label": "Potential conflict"})
            for f in risks(db, actor):
                if f["status"] == "STALE":
                    continue
                nodes[f["id"]] = {"id": f["id"], "label": f["claim"], "kind": "risk", "severity": f["severity"], "href": "/risks"}
                for e in f["evidence"]:
                    key = e["document_key"]
                    nodes[key] = {"id": key, "label": key, "kind": "contract", "href": "/contracts/"+key}
                    clause = key + ":" + e["clause_ref"]
                    nodes[clause] = {"id": clause, "label": e["clause_ref"], "kind": "clause", "href": "/contracts/"+key+"?offset="+str(e["offset"])}
                    edges += [{"id": f["id"]+clause, "source": f["id"], "target": clause, "label": "Cites"}, {"id": clause+key, "source": clause, "target": key, "label": "Belongs to"}]
            return {"nodes": list(nodes.values()), "edges": list({e["id"]: e for e in edges}.values())}

    @router.get("/search")
    def search(q: str = Query(min_length=2, max_length=200), actor=Depends(owner)):
        from .documents import search_documents
        with store.connect() as db:
            results = [{"id": d["document_key"], "group": "Contracts", "title": d["title"], "href": "/contracts/"+d["document_key"]} for d in contracts(db, actor) if q.casefold() in (d["title"]+d["document_key"]).casefold()]
            results += [{"id": c["document_key"]+str(c["offset"]), "group": "Clauses", "title": c["snippet"], "href": "/contracts/"+c["document_key"]+"?offset="+str(c["offset"])} for c in search_documents(db, actor, q)]
            results += [{"id": f["id"], "group": "Risks", "title": f["claim"], "href": "/risks"} for f in risks(db, actor) if q.casefold() in f["claim"].casefold()]
            for kind, path in [("report", "/reports/"), ("obligation", "/timeline")]:
                results += [{"id": r["id"], "group": kind.title(), "title": r["title"], "href": path+r["id"] if kind == "report" else path} for r in records(db, actor, kind) if q.casefold() in r["title"].casefold()]
            return results[:50]

    @router.get("/notifications")
    def notifications(actor=Depends(owner)):
        with store.connect() as db:
            return [{"id": r["id"], "title": r["claim"], "href": "/risks", "status": r["review_status"]} for r in risks(db, actor) if r["review_status"] != "Resolved"] + [{"id": a["id"], "title": a["title"], "href": "/actions", "status": a["status"]} for a in records(db, actor, "action") if a["status"] in ["Draft", "Revision requested"]] + [{"id": r["id"], "title": "Analysis failed: "+str(r["error"]), "href": "/contracts/"+r["document_keys"][0]+"/analysis", "status": "Failed"} for r in runs(db, actor) if r["status"] == "FAILED"]

    @router.get("/settings")
    def get_settings(s=Depends(session)):
        with store.connect() as db:
            org = db.execute("SELECT name FROM web_orgs WHERE id=?", (s["org_id"],)).fetchone()
            preferences = records(db, s["org_id"], "preferences")
            members = [dict(r) for r in db.execute("SELECT u.id,u.name,u.email,m.role FROM web_members m JOIN web_users u ON u.id=m.user_id WHERE m.org_id=?", (s["org_id"],))]
        return {"name": s["name"], "organization": org[0], "members": members, "notifications": preferences[0].get("notifications", True) if preferences else True, "provider": "OpenRouter" if settings.openrouter_api_key else "Anthropic" if settings.anthropic_api_key else "Not configured", "event_source": "Manually supplied", "upload_formats": ["txt"], "analysis_limit": 20}

    @router.patch("/settings")
    def update_settings(body: Profile, s=Depends(session)):
        with store.connect() as db:
            current = db.execute("SELECT name FROM web_orgs WHERE id=?", (s["org_id"],)).fetchone()[0]
            if body.organization != current and s["role"] != "admin":
                raise HTTPException(403, "Only administrators can rename the organization")
            db.execute("UPDATE web_users SET name=? WHERE id=?", (body.name, s["user_id"]))
            if s["role"] == "admin":
                db.execute("UPDATE web_orgs SET name=? WHERE id=?", (body.organization, s["org_id"]))
            return save(db, s["org_id"], "preferences", {"notifications": body.notifications}, "preferences:"+s["org_id"])

    @router.post("/members")
    def add_member(body: Member, s=Depends(session)):
        if s["role"] != "admin":
            raise HTTPException(403, "Administrator permission required")
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT id FROM web_users WHERE email=?", (body.email.strip().lower(),)).fetchone()
            if not user:
                raise HTTPException(404, "This person must create an account before being added")
            prior = db.execute("SELECT role FROM web_members WHERE user_id=? AND org_id=?", (user[0], s["org_id"])).fetchone()
            if prior and prior[0] == "admin" and body.role != "admin" and db.execute("SELECT COUNT(*) FROM web_members WHERE org_id=? AND role='admin'", (s["org_id"],)).fetchone()[0] <= 1:
                raise HTTPException(409, "Keep at least one organization administrator")
            db.execute("INSERT INTO web_members VALUES(?,?,?) ON CONFLICT(user_id,org_id) DO UPDATE SET role=excluded.role", (user[0], s["org_id"], body.role))
            Store.audit(db, s["org_id"], "member.update", user[0], "allowed")
        return {"saved": True}

    @router.get("/stream")
    async def stream(request: Request, actor=Depends(owner)):
        async def events():
            previous = ""
            while not await request.is_disconnected():
                try:
                    if not request.headers.get("authorization"):
                        current = session(request)
                        if current["org_id"] != actor:
                            break
                except HTTPException:
                    yield 'event: expired\ndata: {}\n\n'
                    break
                with store.connect() as db:
                    state = json.dumps([(r["id"], r["status"], r["updated_at"]) for r in runs(db, actor)])
                if state != previous:
                    yield 'event: update\ndata: '+state+'\n\n'
                    previous = state
                else:
                    yield ': heartbeat\n\n'
                await asyncio.sleep(5)
        return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    app.include_router(router)
