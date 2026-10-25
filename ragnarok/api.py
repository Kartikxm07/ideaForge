"""Local API. Bearer token is required for every private route."""
from hmac import compare_digest
from datetime import date
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from .config import Settings
from .analysis import cancel_run, create_run, run_view
from .documents import delete_document as remove_document, search_documents, upsert_document, verify_citation
from .model import ModelUnavailable, ClaudeProvider
from .operational_events import OperationalEvent, add_event, list_events
from .store import Store
from .tools import Step, TOOL_INFO
from .workflow import approve_step, cancel_task, create_task, task_view
from .web_auth import install_auth
from .workspace_api import install_workspace


class TaskRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    steps: list[Step] = Field(min_length=1, max_length=8)


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class ApprovalRequest(BaseModel):
    ordinal: int = Field(ge=0)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    kind: str = Field(default="semantic", pattern="^(semantic|episodic)$")


class DocumentRequest(BaseModel):
    document_key: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2_000_000)


class CitationRequest(BaseModel):
    document_key: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")
    clause_ref: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=1000)


class AnalysisRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    focus: str = Field(min_length=2, max_length=100)
    document_keys: list[str] = Field(min_length=1, max_length=3)
    provider_kind: str = Field(default="anthropic", pattern="^(anthropic|ollama|deterministic)$")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = Store(settings.db_path)
    store.migrate()
    model = ClaudeProvider(settings)
    app = FastAPI(title="Ragnarok Local Runtime", version="0.1.0")
    session = install_auth(app, store)

    async def owner(authorization: str | None = Header(default=None)) -> str:
        token = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
        if not compare_digest(token, settings.api_token):
            raise HTTPException(status_code=401, detail="Authentication required")
        return settings.owner_id

    def workspace_owner(request: Request, authorization: str | None = Header(default=None)) -> str:
        token = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
        if token and compare_digest(token, settings.api_token):
            return settings.owner_id
        return session(request)["org_id"]

    install_workspace(app, store, settings, workspace_owner, session)

    @app.get("/")
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/thor/")

    @app.get("/health/live")
    async def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready(actor: str = Depends(owner)):
        with store.connect() as db:
            db.execute("SELECT 1").fetchone()
        return {"status": "ok", "owner_id": actor, "privacy_mode": "local-only"}

    @app.get("/api/v1/models/health")
    async def model_health(_: str = Depends(owner)):
        return model.health()

    @app.get("/api/v1/tools")
    async def tools(_: str = Depends(owner)):
        return [{"id": key, **value} for key, value in TOOL_INFO.items()]

    @app.post("/api/v1/tasks", status_code=201)
    async def new_task(request: TaskRequest, idempotency_key: str | None = Header(default=None, max_length=128), actor: str = Depends(owner)):
        try:
            return create_task(store, actor, request.prompt, request.steps, idempotency_key)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/tasks/from-prompt", status_code=201)
    async def task_from_prompt(request: PromptRequest, idempotency_key: str | None = Header(default=None, max_length=128), actor: str = Depends(owner)):
        try:
            steps = model.plan(request.prompt)
            return create_task(store, actor, request.prompt, steps, idempotency_key)
        except ModelUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/tasks")
    async def list_tasks(limit: int = Query(default=20, ge=1, le=100), actor: str = Depends(owner)):
        with store.connect() as db:
            ids = db.execute("SELECT id FROM tasks WHERE owner_id=? ORDER BY created_at DESC LIMIT ?", (actor, limit)).fetchall()
            return [task_view(db, row["id"], actor) for row in ids]

    @app.get("/api/v1/tasks/{task_id}")
    async def get_task(task_id: str, actor: str = Depends(owner)):
        with store.connect() as db:
            result = task_view(db, task_id, actor)
        if result is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return result

    @app.get("/api/v1/tasks/{task_id}/events")
    async def get_events(task_id: str, after: int = Query(default=0, ge=0), actor: str = Depends(owner)):
        with store.connect() as db:
            if task_view(db, task_id, actor) is None:
                raise HTTPException(status_code=404, detail="Task not found")
            rows = db.execute("SELECT id,type,message,created_at FROM events WHERE task_id=? AND owner_id=? AND id>? ORDER BY id LIMIT 100", (task_id, actor, after)).fetchall()
            return [dict(row) for row in rows]

    @app.post("/api/v1/tasks/{task_id}/approve")
    async def approve(task_id: str, request: ApprovalRequest, actor: str = Depends(owner)):
        try:
            result = approve_step(store, actor, task_id, request.ordinal, request.digest)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return result

    @app.post("/api/v1/tasks/{task_id}/cancel")
    async def cancel(task_id: str, actor: str = Depends(owner)):
        try:
            result = cancel_task(store, actor, task_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return result

    @app.get("/api/v1/memories")
    async def memories(q: str = Query(default="", max_length=200), limit: int = Query(default=20, ge=1, le=100), actor: str = Depends(owner)):
        with store.connect() as db:
            rows = db.execute("SELECT * FROM memories WHERE owner_id=? AND content LIKE ? ORDER BY created_at DESC LIMIT ?", (actor, f"%{q}%", limit)).fetchall()
            return [dict(row) for row in rows]

    @app.post("/api/v1/memories", status_code=201)
    async def add_memory(request: MemoryRequest, actor: str = Depends(owner)):
        from uuid import uuid4
        from .store import now
        memory_id = str(uuid4())
        with store.connect() as db:
            db.execute("INSERT INTO memories(id,owner_id,kind,content,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (memory_id, actor, request.kind, request.content, "user", now(), now()))
            Store.audit(db, actor, "memory.create", memory_id, "allowed")
            return dict(db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone())

    @app.put("/api/v1/memories/{memory_id}")
    async def edit_memory(memory_id: str, request: MemoryRequest, actor: str = Depends(owner)):
        from .store import now
        with store.connect() as db:
            changed = db.execute("UPDATE memories SET content=?,kind=?,updated_at=? WHERE id=? AND owner_id=?", (request.content, request.kind, now(), memory_id, actor)).rowcount
            if not changed:
                raise HTTPException(status_code=404, detail="Memory not found")
            Store.audit(db, actor, "memory.edit", memory_id, "allowed")
            return dict(db.execute("SELECT * FROM memories WHERE id=? AND owner_id=?", (memory_id, actor)).fetchone())

    @app.delete("/api/v1/memories/{memory_id}", status_code=204)
    async def delete_memory(memory_id: str, actor: str = Depends(owner)):
        with store.connect() as db:
            changed = db.execute("DELETE FROM memories WHERE id=? AND owner_id=?", (memory_id, actor)).rowcount
            if not changed:
                raise HTTPException(status_code=404, detail="Memory not found")
            Store.audit(db, actor, "memory.delete", memory_id, "allowed")

    @app.get("/api/v1/memories/export")
    async def export_memories(actor: str = Depends(owner)):
        with store.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM memories WHERE owner_id=? ORDER BY created_at", (actor,)).fetchall()]

    @app.get("/api/v1/audit")
    async def audit(limit: int = Query(default=50, ge=1, le=100), actor: str = Depends(owner)):
        with store.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM audit_events WHERE owner_id=? ORDER BY id DESC LIMIT ?", (actor, limit)).fetchall()]

    @app.post("/api/v1/documents", status_code=201)
    async def add_document(request: DocumentRequest, actor: str = Depends(owner)):
        try:
            return upsert_document(store, actor, request.document_key, request.title, request.content, "api")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/documents")
    async def list_documents(limit: int = Query(default=100, ge=1, le=100), actor: str = Depends(owner)):
        with store.connect() as db:
            return [dict(row) for row in db.execute("SELECT id,document_key,title,content_sha256,source,created_at,updated_at FROM documents WHERE owner_id=? ORDER BY document_key LIMIT ?", (actor, limit)).fetchall()]

    @app.get("/api/v1/documents/search")
    async def document_search(q: str = Query(min_length=1, max_length=200), limit: int = Query(default=20, ge=1, le=100), actor: str = Depends(owner)):
        with store.connect() as db:
            return search_documents(db, actor, q, limit)

    @app.get("/api/v1/documents/{document_key}")
    async def get_document(document_key: str, actor: str = Depends(owner)):
        with store.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE owner_id=? AND document_key=?", (actor, document_key)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Document not found")
            return dict(row)

    @app.delete("/api/v1/documents/{document_key}", status_code=204)
    async def delete_document(document_key: str, actor: str = Depends(owner)):
        if not remove_document(store, actor, document_key):
            raise HTTPException(status_code=404, detail="Document not found")

    @app.post("/api/v1/citations/verify")
    async def verify(request: CitationRequest, actor: str = Depends(owner)):
        with store.connect() as db:
            try:
                return verify_citation(db, actor, request.document_key, request.clause_ref, request.quote)
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/analyses", status_code=201)
    async def new_analysis(request: AnalysisRequest, idempotency_key: str | None = Header(default=None, max_length=128), actor: str = Depends(owner)):
        try:
            return create_run(store, actor, request.question, request.focus, request.document_keys, idempotency_key, request.provider_kind)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/analyses")
    async def list_analyses(limit: int = Query(default=20, ge=1, le=100), actor: str = Depends(owner)):
        with store.connect() as db:
            ids = db.execute("SELECT id FROM analysis_runs WHERE owner_id=? ORDER BY created_at DESC LIMIT ?", (actor, limit)).fetchall()
            return [run_view(db, actor, row["id"]) for row in ids]

    @app.get("/api/v1/analyses/{run_id}")
    async def get_analysis(run_id: str, actor: str = Depends(owner)):
        with store.connect() as db:
            result = run_view(db, actor, run_id)
            if result is None:
                raise HTTPException(status_code=404, detail="Analysis not found")
            return result

    @app.post("/api/v1/analyses/{run_id}/cancel")
    async def cancel_analysis(run_id: str, actor: str = Depends(owner)):
        try:
            result = cancel_run(store, actor, run_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return result

    @app.post("/api/v1/operational-events", status_code=201)
    async def new_operational_event(request: OperationalEvent, actor: str = Depends(owner)):
        try:
            created = add_event(store, actor, request)
            return {"event_id": request.event_id, "created": created}
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/v1/operational-events")
    async def operational_event_list(as_of: date | None = None, limit: int = Query(default=100, ge=1, le=500), actor: str = Depends(owner)):
        with store.connect() as db:
            return list_events(db, actor, as_of, limit)

    @app.get("/api/v1/operational-events/{event_id}")
    async def get_operational_event(event_id: str, actor: str = Depends(owner)):
        with store.connect() as db:
            row = db.execute("SELECT * FROM operational_events WHERE owner_id=? AND event_id=?", (actor, event_id)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Event not found")
            return dict(row)

    @app.delete("/api/v1/operational-events/{event_id}", status_code=204)
    async def delete_operational_event(event_id: str, actor: str = Depends(owner)):
        with store.connect() as db:
            changed = db.execute("DELETE FROM operational_events WHERE owner_id=? AND event_id=?", (actor, event_id)).rowcount
            if not changed:
                raise HTTPException(status_code=404, detail="Event not found")
            Store.audit(db, actor, "event.delete", event_id, "allowed")

    @app.get("/api/v1/event-import-errors")
    async def event_import_errors(limit: int = Query(default=100, ge=1, le=500), actor: str = Depends(owner)):
        with store.connect() as db:
            rows = db.execute("SELECT source_file,line_number,line_sha256,error_type,recorded_at FROM event_import_errors WHERE owner_id=? ORDER BY recorded_at DESC,line_number LIMIT ?", (actor, limit)).fetchall()
            return [dict(row) for row in rows]

    try:
        from thor_agent.server import app as thor_app
        app.mount("/thor", thor_app)
    except Exception:
        pass

    return app
