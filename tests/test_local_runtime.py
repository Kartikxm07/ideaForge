import os
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import httpx
from ragnarok.api import create_app
from ragnarok.config import Settings
from ragnarok.store import Store
from ragnarok.documents import import_odin_bundle
from ragnarok.analysis import FindingBatch, create_run, run_analysis_once
from ragnarok.operational_events import import_event_drop
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


def test_document_ingestion_citation_and_owner_scope(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    alice = LocalClient(create_app(settings(path)))
    bob = LocalClient(create_app(settings(path, "bob")))
    bundle = tmp_path / "bundle"
    (bundle / "contracts").mkdir(parents=True)
    content = "Section A — Terms\nNotice is due in 30 days.\nSection B — Other\nNo refund is due.\n"
    (bundle / "contracts" / "A1.txt").write_text(content, encoding="utf-8")
    (bundle / "manifest.json").write_text(json.dumps({"files": [{"path": "contracts/A1.txt", "title": "Sample contract"}]}), encoding="utf-8")
    imported = import_odin_bundle(Store(path), "alice", bundle)
    assert len(imported) == 1 and imported[0]["document_key"] == "A1"
    assert bob.get("/api/v1/documents", headers=HEADERS).json() == []
    results = alice.get("/api/v1/documents/search", headers=HEADERS, params={"q": "Notice is due"}).json()
    assert results[0]["heading"] == "Section A — Terms"
    citation = {"document_key": "A1", "clause_ref": "Section A", "quote": "Notice is due in 30 days."}
    original = alice.post("/api/v1/citations/verify", headers=HEADERS, json=citation).json()
    assert original["verified"] is True
    assert alice.post("/api/v1/citations/verify", headers=HEADERS, json={**citation, "clause_ref": "Section B"}).json()["verified"] is False
    assert bob.post("/api/v1/citations/verify", headers=HEADERS, json=citation).status_code == 404
    updated = alice.post("/api/v1/documents", headers=HEADERS, json={"document_key": "A1", "title": "Revised sample", "content": "Section A — Terms\nNotice is due in 45 days.\n"}).json()
    assert updated["content_sha256"] != original["content_sha256"]
    assert alice.post("/api/v1/citations/verify", headers=HEADERS, json=citation).json()["verified"] is False
    assert alice.delete("/api/v1/documents/A1", headers=HEADERS).status_code == 204
    assert alice.get("/api/v1/documents/search", headers=HEADERS, params={"q": "Notice"}).json() == []


def test_odin_manifest_rejects_path_escape(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    Store(path).migrate()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text(json.dumps({"files": [{"path": "contracts/../../secret.txt", "title": "Bad"}]}), encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    import pytest
    with pytest.raises((ValueError, FileNotFoundError)):
        import_odin_bundle(Store(path), "alice", bundle)


def test_schema_upgrades_existing_local_database(tmp_path):
    import sqlite3
    path = tmp_path / "old.sqlite3"
    first = Path(__file__).resolve().parents[1] / "ragnarok" / "migrations" / "001_init.sql"
    with sqlite3.connect(path) as db:
        db.executescript(first.read_text(encoding="utf-8"))
        db.execute("PRAGMA user_version=1")
    Store(path).migrate()
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 6
        assert db.execute("SELECT name FROM sqlite_master WHERE name='documents'").fetchone() is not None
        assert db.execute("SELECT name FROM sqlite_master WHERE name='analysis_runs'").fetchone() is not None
        assert db.execute("SELECT name FROM sqlite_master WHERE name='operational_events'").fetchone() is not None
        assert db.execute("SELECT name FROM sqlite_master WHERE name='event_import_errors'").fetchone() is not None
        assert db.execute("SELECT name FROM sqlite_master WHERE name='odin_workstreams'").fetchone() is not None


def test_evidence_checked_analysis_rejects_bad_quotes_and_stales_on_update(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    alice = LocalClient(create_app(settings(path)))
    bob = LocalClient(create_app(settings(path, "bob")))
    for key, text in [("A1", "Section D — Uptime\nProvider promises 99.95% uptime.\n"),
                      ("B1", "Section D — Uptime\nCustomer receives 99.9% uptime.\n")]:
        assert alice.post("/api/v1/documents", headers=HEADERS, json={"document_key": key, "title": key, "content": text}).status_code == 201
    request = {"question": "Compare uptime commitments", "focus": "uptime", "document_keys": ["A1", "B1"]}
    headers = {**HEADERS, "Idempotency-Key": "compare-uptime"}
    run = alice.post("/api/v1/analyses", headers=headers, json=request).json()
    assert run["status"] == "READY"
    assert alice.post("/api/v1/analyses", headers=headers, json=request).json()["id"] == run["id"]
    assert bob.get(f"/api/v1/analyses/{run['id']}", headers=HEADERS).status_code == 404

    class FakeProvider:
        def propose_findings(self, question, contexts):
            assert question == request["question"]
            assert {item["document_key"] for item in contexts} == {"A1", "B1"}
            return FindingBatch.model_validate({"findings": [
                {"claim": "Different uptime figures", "explanation": "Review the different percentages.", "evidence": [
                    {"document_key": "A1", "clause_ref": "Section D", "quote": "Provider promises 99.95% uptime."},
                    {"document_key": "B1", "clause_ref": "Section D", "quote": "Customer receives 99.9% uptime."},
                ]},
                {"claim": "Unsupported claim", "explanation": "Bad quote", "evidence": [
                    {"document_key": "A1", "clause_ref": "Section D", "quote": "Provider promises 100% uptime."},
                ]},
            ]})

    with Store(path).connect() as db:
        db.execute("UPDATE analysis_runs SET status='RUNNING',lease_until='2000-01-01T00:00:00+00:00' WHERE id=?", (run["id"],))
    assert run_analysis_once(Store(path), "alice", FakeProvider()) is True
    completed = alice.get(f"/api/v1/analyses/{run['id']}", headers=HEADERS).json()
    assert completed["status"] == "COMPLETED"
    assert completed["rejected_count"] == 1
    assert len(completed["findings"]) == 1
    assert completed["findings"][0]["status"] == "EVIDENCE_CHECKED"
    assert alice.post("/api/v1/documents", headers=HEADERS, json={"document_key": "A1", "title": "A1", "content": "Section D — Uptime\nProvider promises 99.5% uptime.\n"}).status_code == 201
    stale = alice.get(f"/api/v1/analyses/{run['id']}", headers=HEADERS).json()
    assert stale["status"] == "STALE" and stale["findings"][0]["status"] == "STALE"
    assert alice.delete("/api/v1/documents/A1", headers=HEADERS).status_code == 204
    assert alice.get(f"/api/v1/analyses/{run['id']}", headers=HEADERS).status_code == 404


def test_analysis_model_failure_is_recorded(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    client = LocalClient(create_app(settings(path)))
    client.post("/api/v1/documents", headers=HEADERS, json={"document_key": "A1", "title": "A1", "content": "Section A — Terms\nUptime is 99%.\n"})
    run = client.post("/api/v1/analyses", headers=HEADERS, json={"question": "Check uptime", "focus": "Uptime", "document_keys": ["A1"]}).json()

    class BrokenProvider:
        def propose_findings(self, question, contexts):
            raise RuntimeError("offline")

    assert run_analysis_once(Store(path), "alice", BrokenProvider()) is True
    failed = client.get(f"/api/v1/analyses/{run['id']}", headers=HEADERS).json()
    assert failed["status"] == "FAILED" and failed["error"] == "RuntimeError"


def test_offline_uptime_comparison_is_grounded(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    client = LocalClient(create_app(settings(path)))
    sources = {
        "A2": "SECTION 2 — UPTIME COMMITMENT\n2.1  Provider promises 99.5% of minutes.\n",
        "B1": "§3.1  Uptime Commitment. Customer receives 99.9% of minutes.\n",
    }
    for key, content in sources.items():
        client.post("/api/v1/documents", headers=HEADERS, json={"document_key": key, "title": key, "content": content})
    run = client.post("/api/v1/analyses", headers=HEADERS, json={"question": "Compare uptime", "focus": "Uptime", "document_keys": ["A2", "B1"], "provider_kind": "deterministic"}).json()

    class UnusedProvider:
        def propose_findings(self, question, contexts):
            raise AssertionError("Ollama must not be used in deterministic mode")

    assert run_analysis_once(Store(path), "alice", UnusedProvider()) is True
    result = client.get(f"/api/v1/analyses/{run['id']}", headers=HEADERS).json()
    assert result["status"] == "COMPLETED"
    assert len(result["findings"]) == 1
    assert result["findings"][0]["status"] == "EVIDENCE_CHECKED"
    assert {item["document_key"] for item in result["findings"][0]["evidence"]} == {"A2", "B1"}


def test_citation_can_match_later_identical_quote(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    client = LocalClient(create_app(settings(path)))
    content = "Section A — First\nSame sentence.\nSection B — Second\nSame sentence.\n"
    client.post("/api/v1/documents", headers=HEADERS, json={"document_key": "D", "title": "D", "content": content})
    result = client.post("/api/v1/citations/verify", headers=HEADERS, json={"document_key": "D", "clause_ref": "Section B", "quote": "Same sentence."}).json()
    assert result["verified"] is True
    assert result["heading"] == "Section B — Second"


def test_event_drops_are_atomic_idempotent_and_checkpointed(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    alice = LocalClient(create_app(settings(path)))
    bob = LocalClient(create_app(settings(path, "bob")))

    def event(event_id, timestamp, subject):
        return {"event_id": event_id, "timestamp": timestamp, "channel": "email", "from": "Sender", "to": "Recipient", "subject": subject, "body": "Event body"}

    first = tmp_path / "drop1.jsonl"
    first.write_text(json.dumps(event("E-01", "2027-01-22T09:30:00Z", "January notice")) + "\n", encoding="utf-8")
    second = tmp_path / "drop2.jsonl"
    second.write_text(json.dumps(event("E-02", "2027-06-01T15:00:00Z", "June incident")) + "\n", encoding="utf-8")
    assert import_event_drop(Store(path), "alice", first) == {"records": 1, "created": 1, "duplicates": 0, "quarantined": 0}
    assert import_event_drop(Store(path), "alice", first) == {"records": 1, "created": 0, "duplicates": 1, "quarantined": 0}
    assert import_event_drop(Store(path), "alice", second)["created"] == 1
    march = alice.get("/api/v1/operational-events", headers=HEADERS, params={"as_of": "2027-03-15"}).json()
    assert [row["event_id"] for row in march] == ["E-01"]
    assert len(alice.get("/api/v1/operational-events", headers=HEADERS).json()) == 2
    assert bob.get("/api/v1/operational-events", headers=HEADERS).json() == []
    assert bob.get("/api/v1/operational-events/E-01", headers=HEADERS).status_code == 404

    conflicting = tmp_path / "conflict.jsonl"
    conflicting.write_text("\n".join([
        json.dumps(event("E-03", "2027-07-01T00:00:00Z", "New")),
        json.dumps(event("E-01", "2027-01-22T09:30:00Z", "Changed")),
    ]) + "\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError):
        import_event_drop(Store(path), "alice", conflicting)
    assert alice.get("/api/v1/operational-events/E-03", headers=HEADERS).status_code == 404
    assert alice.delete("/api/v1/operational-events/E-01", headers=HEADERS).status_code == 204
    assert alice.get("/api/v1/operational-events/E-01", headers=HEADERS).status_code == 404


def test_malformed_event_line_is_quarantined_without_losing_valid_records(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    client = LocalClient(create_app(settings(path)))
    drop = tmp_path / "drop.jsonl"
    valid = {"event_id": "E-18", "timestamp": "2027-07-01T08:00:00Z", "channel": "email", "from": "A", "to": "B", "subject": "Invoice", "body": "Issued"}
    drop.write_text(json.dumps(valid) + "\nnot json\n", encoding="utf-8")
    assert import_event_drop(Store(path), "alice", drop) == {"records": 2, "created": 1, "duplicates": 0, "quarantined": 1}
    assert import_event_drop(Store(path), "alice", drop) == {"records": 2, "created": 0, "duplicates": 1, "quarantined": 1}
    errors = client.get("/api/v1/event-import-errors", headers=HEADERS).json()
    assert len(errors) == 1 and errors[0]["line_number"] == 2 and errors[0]["error_type"] == "JSONDecodeError"
    assert client.get("/api/v1/operational-events/E-18", headers=HEADERS).status_code == 200

