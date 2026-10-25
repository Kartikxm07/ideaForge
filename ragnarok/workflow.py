"""Durable, bounded workflow state machine and one-step worker."""
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import uuid
from .store import Store, now
from .tools import Step, TOOL_INFO, approval_digest, execute, validate_steps


def task_view(db: sqlite3.Connection, task_id: str, owner_id: str) -> dict | None:
    row = db.execute("SELECT * FROM tasks WHERE id=? AND owner_id=?", (task_id, owner_id)).fetchone()
    if row is None:
        return None
    steps = db.execute("SELECT ordinal,tool_id,status,output_json,approval_digest,approved FROM steps WHERE task_id=? ORDER BY ordinal", (task_id,)).fetchall()
    return {
        "id": row["id"], "prompt": row["prompt"], "status": row["status"],
        "created_at": row["created_at"], "updated_at": row["updated_at"], "error": row["error"],
        "steps": [{"ordinal": s["ordinal"], "tool_id": s["tool_id"], "status": s["status"],
                   "output": json.loads(s["output_json"]) if s["output_json"] else None,
                   "approval_digest": s["approval_digest"] if not s["approved"] else None} for s in steps],
    }


def create_task(store: Store, owner_id: str, prompt: str, steps: list[Step], idempotency_key: str | None) -> dict:
    validate_steps(steps)
    task_id = str(uuid.uuid4())
    requires_approval = any(TOOL_INFO[s.tool_id]["approval"] for s in steps)
    status = "AWAITING_APPROVAL" if requires_approval else "READY"
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            prior = db.execute("SELECT id,prompt,plan_json FROM tasks WHERE owner_id=? AND idempotency_key=?", (owner_id, idempotency_key)).fetchone()
            if prior:
                if prior["prompt"] != prompt or prior["plan_json"] != json.dumps([s.model_dump() for s in steps]):
                    raise ValueError("Idempotency key was already used for a different task")
                return task_view(db, prior["id"], owner_id)
        db.execute(
            "INSERT INTO tasks(id,owner_id,prompt,status,plan_json,idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (task_id, owner_id, prompt, status, json.dumps([s.model_dump() for s in steps]), idempotency_key, now(), now()),
        )
        for ordinal, step in enumerate(steps):
            db.execute(
                "INSERT INTO steps(task_id,ordinal,tool_id,arguments_json,approval_digest,status) VALUES(?,?,?,?,?,?)",
                (task_id, ordinal, step.tool_id, step.model_dump_json(), approval_digest(step) if TOOL_INFO[step.tool_id]["approval"] else None, "PENDING"),
            )
        Store.event(db, task_id, owner_id, "created", f"Task created with {len(steps)} steps")
        Store.audit(db, owner_id, "task.create", task_id, "allowed")
        return task_view(db, task_id, owner_id)


def approve_step(store: Store, owner_id: str, task_id: str, ordinal: int, digest: str) -> dict | None:
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        task = db.execute("SELECT status FROM tasks WHERE id=? AND owner_id=?", (task_id, owner_id)).fetchone()
        if task is None:
            return None
        if task["status"] != "AWAITING_APPROVAL":
            raise ValueError("Task is not awaiting approval")
        updated = db.execute(
            "UPDATE steps SET approved=1 WHERE task_id=? AND ordinal=? AND approval_digest=? AND approved=0",
            (task_id, ordinal, digest),
        ).rowcount
        if not updated:
            Store.audit(db, owner_id, "step.approve", task_id, "denied")
            raise ValueError("Approval does not match the exact step")
        remaining = db.execute("SELECT COUNT(*) FROM steps WHERE task_id=? AND approval_digest IS NOT NULL AND approved=0", (task_id,)).fetchone()[0]
        if remaining == 0:
            db.execute("UPDATE tasks SET status='READY',updated_at=? WHERE id=?", (now(), task_id))
        Store.event(db, task_id, owner_id, "approved", f"Step {ordinal} approved")
        Store.audit(db, owner_id, "step.approve", task_id, "allowed")
        return task_view(db, task_id, owner_id)


def cancel_task(store: Store, owner_id: str, task_id: str) -> dict | None:
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT status FROM tasks WHERE id=? AND owner_id=?", (task_id, owner_id)).fetchone()
        if row is None:
            return None
        if row["status"] not in {"READY", "AWAITING_APPROVAL"}:
            raise ValueError("Only queued tasks can be cancelled")
        db.execute("UPDATE tasks SET status='CANCELLED',updated_at=? WHERE id=?", (now(), task_id))
        Store.event(db, task_id, owner_id, "cancelled", "Task cancelled")
        Store.audit(db, owner_id, "task.cancel", task_id, "allowed")
        return task_view(db, task_id, owner_id)


def run_once(store: Store, owner_id: str) -> bool:
    """Claim one step. Expired claims are retried only for idempotent built-in tools."""
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        task = db.execute(
            "SELECT id FROM tasks WHERE owner_id=? AND status IN ('READY','RUNNING') "
            "AND (lease_until IS NULL OR lease_until<?) ORDER BY created_at LIMIT 1",
            (owner_id, now()),
        ).fetchone()
        if task is None:
            return False
        task_id = task["id"]
        step = db.execute("SELECT * FROM steps WHERE task_id=? AND status!='COMPLETED' ORDER BY ordinal LIMIT 1", (task_id,)).fetchone()
        if step is None:
            db.execute("UPDATE tasks SET status='COMPLETED',lease_until=NULL,updated_at=? WHERE id=?", (now(), task_id))
            Store.event(db, task_id, owner_id, "completed", "All steps completed")
            return True
        if step["approval_digest"] and not step["approved"]:
            db.execute("UPDATE tasks SET status='AWAITING_APPROVAL',lease_until=NULL,updated_at=? WHERE id=?", (now(), task_id))
            return True
        lease_until = (datetime.now(timezone.utc) + timedelta(seconds=45)).isoformat()
        db.execute("UPDATE tasks SET status='RUNNING',lease_until=?,updated_at=? WHERE id=?", (lease_until, now(), task_id))
        db.execute("UPDATE steps SET status='RUNNING',started_at=? WHERE task_id=? AND ordinal=?", (now(), task_id, step["ordinal"]))
        Store.event(db, task_id, owner_id, "step_started", f"Step {step['ordinal']} started: {step['tool_id']}")

    try:
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT output_json FROM steps WHERE task_id=? AND ordinal=?", (task_id, step["ordinal"] - 1)).fetchone()
            previous = json.loads(prior["output_json"]) if prior and prior["output_json"] else None
            spec = Step.model_validate_json(step["arguments_json"])
            # Recheck the exact approved arguments at execution time.
            if step["approval_digest"] and (not step["approved"] or approval_digest(spec) != step["approval_digest"]):
                raise ValueError("Step approval is invalid")
            output = execute(db, task_id, step["ordinal"], owner_id, spec, previous)
            db.execute("UPDATE steps SET status='COMPLETED',output_json=?,completed_at=? WHERE task_id=? AND ordinal=?", (json.dumps(output), now(), task_id, step["ordinal"]))
            remaining = db.execute("SELECT COUNT(*) FROM steps WHERE task_id=? AND status!='COMPLETED'", (task_id,)).fetchone()[0]
            status = "COMPLETED" if remaining == 0 else "READY"
            db.execute("UPDATE tasks SET status=?,lease_until=NULL,updated_at=? WHERE id=?", (status, now(), task_id))
            Store.event(db, task_id, owner_id, "step_completed", f"Step {step['ordinal']} completed")
            if status == "COMPLETED":
                Store.event(db, task_id, owner_id, "completed", "All steps completed")
        return True
    except Exception as exc:
        with store.connect() as db:
            db.execute("UPDATE tasks SET status='FAILED',error=?,lease_until=NULL,updated_at=? WHERE id=?", (type(exc).__name__, now(), task_id))
            Store.event(db, task_id, owner_id, "failed", f"Step {step['ordinal']} failed: {type(exc).__name__}")
        return True
