"""Closed registry of deterministic local tools; no shell or arbitrary network access."""
from hashlib import sha256
import json
import re
import sqlite3
import uuid
from pydantic import BaseModel, ConfigDict, Field
from .store import now


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_id: str
    text: str = Field(min_length=1, max_length=4000)
    use_previous: bool = False


TOOL_INFO = {
    "text.uppercase": {"description": "Uppercase local text", "approval": False, "risk": "low"},
    "text.word_count": {"description": "Count words in local text", "approval": False, "risk": "low"},
    "memory.save": {"description": "Save text as a local semantic memory", "approval": True, "risk": "medium"},
}


def validate_steps(steps: list[Step]) -> None:
    if not 1 <= len(steps) <= 8:
        raise ValueError("A task needs 1 to 8 steps")
    for index, step in enumerate(steps):
        if step.tool_id not in TOOL_INFO:
            raise ValueError(f"Unapproved tool: {step.tool_id}")
        if step.use_previous and index == 0:
            raise ValueError("First step cannot use a previous result")


def approval_digest(step: Step) -> str:
    return sha256(step.model_dump_json().encode("utf-8")).hexdigest()


def execute(db: sqlite3.Connection, task_id: str, ordinal: int, owner_id: str, step: Step, previous: str | None) -> str:
    value = previous if step.use_previous else step.text
    if value is None:
        raise ValueError("Previous step has no result")
    if step.tool_id == "text.uppercase":
        return value.upper()
    if step.tool_id == "text.word_count":
        return str(len(re.findall(r"\b[\w'-]+\b", value)))
    if step.tool_id == "memory.save":
        memory_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ragnarok:{task_id}:{ordinal}"))
        db.execute(
            "INSERT OR IGNORE INTO memories(id,owner_id,kind,content,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (memory_id, owner_id, "semantic", value, f"task:{task_id}", now(), now()),
        )
        return memory_id
    raise ValueError("Unapproved tool")

