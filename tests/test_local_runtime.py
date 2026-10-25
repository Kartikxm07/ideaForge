import os
import asyncio
from pathlib import Path
import subprocess
import sys
import httpx
from ragnarok.api import create_app
from ragnarok.config import Settings
from ragnarok.store import Store
from ragnarok.workflow import run_once


TOKEN = "a" * 40
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


class LocalClient:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://local") as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)


def settings(path: Path, owner: str = "alice") -> Settings:
    return Settings(TOKEN, owner, path, "http://127.0.0.1:11434", "missing-model")


def test_auth_and_tenant_isolation(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    alice = LocalClient(create_app(settings(path)))
    bob = LocalClient(create_app(settings(path, "bob")))
    assert alice.get("/api/v1/tasks").status_code == 401
    task = alice.post("/api/v1/tasks", headers=HEADERS, json={"prompt": "shout", "steps": [{"tool_id": "text.uppercase", "text": "hello"}]}).json()
    assert bob.get(f"/api/v1/tasks/{task['id']}", headers=HEADERS).status_code == 404
    assert bob.get("/api/v1/tasks", headers=HEADERS).json() == []
    memory = alice.post("/api/v1/memories", headers=HEADERS, json={"content": "private"}).json()
    assert bob.get("/api/v1/memories", headers=HEADERS).json() == []
    assert bob.delete(f"/api/v1/memories/{memory['id']}", headers=HEADERS).status_code == 404


def test_approval_idempotency_and_memory_deletion(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    client = LocalClient(create_app(settings(path)))
    body = {"prompt": "remember", "steps": [{"tool_id": "memory.save", "text": "red fox"}]}
    headers = {**HEADERS, "Idempotency-Key": "remember-red-fox"}
    task = client.post("/api/v1/tasks", headers=headers, json=body).json()
    duplicate = client.post("/api/v1/tasks", headers=headers, json=body).json()
    assert duplicate["id"] == task["id"]
    assert client.post("/api/v1/tasks", headers=headers, json={"prompt": "different", "steps": body["steps"]}).status_code == 422
    assert task["status"] == "AWAITING_APPROVAL"
    assert run_once(Store(path), "alice") is False
    assert client.post(f"/api/v1/tasks/{task['id']}/approve", headers=HEADERS, json={"ordinal": 0, "digest": "0" * 64}).status_code == 409
    digest = task["steps"][0]["approval_digest"]
    assert client.post(f"/api/v1/tasks/{task['id']}/approve", headers=HEADERS, json={"ordinal": 0, "digest": digest}).json()["status"] == "READY"
    assert run_once(Store(path), "alice") is True
    completed = client.get(f"/api/v1/tasks/{task['id']}", headers=HEADERS).json()
    assert completed["status"] == "COMPLETED"
    memories = client.get("/api/v1/memories", headers=HEADERS).json()
    assert len(memories) == 1 and memories[0]["content"] == "red fox"
    assert client.delete(f"/api/v1/memories/{memories[0]['id']}", headers=HEADERS).status_code == 204
    assert client.get("/api/v1/memories", headers=HEADERS).json() == []


def test_worker_restarts_without_repeating_completed_step(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    client = LocalClient(create_app(settings(path)))
    task = client.post("/api/v1/tasks", headers=HEADERS, json={"prompt": "two steps", "steps": [
        {"tool_id": "text.uppercase", "text": "hello world"},
        {"tool_id": "text.word_count", "text": "ignored", "use_previous": True},
    ]}).json()
    env = {**os.environ, "RAGNAROK_API_TOKEN": TOKEN, "RAGNAROK_OWNER_ID": "alice", "RAGNAROK_DB_PATH": str(path)}
    for _ in range(2):
        result = subprocess.run([sys.executable, "-m", "ragnarok.cli", "worker", "--once"], env=env, capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
    completed = client.get(f"/api/v1/tasks/{task['id']}", headers=HEADERS).json()
    assert completed["status"] == "COMPLETED"
    assert [step["output"] for step in completed["steps"]] == ["HELLO WORLD", "2"]
    events = client.get(f"/api/v1/tasks/{task['id']}/events", headers=HEADERS).json()
    assert len([event for event in events if event["type"] == "step_completed"]) == 2


def test_unavailable_model_and_tool_rejection(tmp_path):
    client = LocalClient(create_app(settings(tmp_path / "runtime.sqlite3")))
    assert client.post("/api/v1/tasks", headers=HEADERS, json={"prompt": "bad", "steps": [{"tool_id": "shell.run", "text": "whoami"}]}).status_code == 422
    response = client.post("/api/v1/tasks/from-prompt", headers=HEADERS, json={"prompt": "say hi"})
    assert response.status_code == 503

