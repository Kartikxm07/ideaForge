"""Offline integration coverage for LangGraph routing and durable outputs."""
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from ragnarok.agents import execute_run, run_view, start_run
from ragnarok.agent_graph import build_graph
from ragnarok.documents import upsert_document
from ragnarok.operational_events import OperationalEvent, add_event
from ragnarok.store import Store


class DebateModel:
    settings = SimpleNamespace(model_heavy="fake")

    def __init__(self):
        self.calls = []

    def _call(self, prompt, _model, _limit):
        self.calls.append(prompt)
        if "You are Odin" in prompt:
            return '{"objective":"Analyze contracts","workstreams":[{"document_key":"A","focus":["terms"]}]}'
        if "You are Thor" in prompt:
            key = prompt.split("Document key: ", 1)[1].split(".", 1)[0]
            quote = "Customer shall pay $500 on 2027-03-15."
            return json.dumps({"items": [{"field": "payment", "value": quote, "confidence": 0.9,
                "citation": {"document_key": key, "clause_ref": "Section 1. Payment", "quote": quote}}]})
        if "Act as Thor's evidence advocate" in prompt:
            return '{"answer":"The verified payment chunk supports the extracted date.","supported":true,"citation_ids":[]}'
        if "You are Loki, adversarial" in prompt:
            return json.dumps({"findings": [{"claim": "Payment timing may be disputed", "reasoning": "Check both terms",
                "severity": "medium", "citations": [{"document_key": "A", "clause_ref": "Section 1. Payment",
                    "quote": "Customer shall pay $500 on 2027-03-15."}]}]})
        if "You are Heimdall" in prompt:
            verdict = "confirmed" if '"debate_round": 1' in prompt else "challenged"
            return json.dumps({"verdict": verdict, "reason": "Evidence checked", "event_ids": []})
        if "You are Loki. A proposed risk" in prompt:
            return '{"rebuttal":"The cited payment clause supports the date."}'
        if "You are Tyr" in prompt:
            return '{"outcome":"needs_review","rationale":"Human interpretation needed","draft_notice":null}'
        raise AssertionError("Unexpected graph stage")


def test_graph_fans_out_and_debates_once(tmp_path):
    store = Store(tmp_path / "odin.sqlite3")
    store.migrate()
    source = "Section 1. Payment\nCustomer shall pay $500 on 2027-03-15.\n"
    for key in ("B", "A"):
        upsert_document(store, "org", key, key, source, "test")
    run = start_run(store, "org", ["B", "A"])
    model = DebateModel()
    execute_run(store, "org", run["id"], model)
    result = run_view(store, "org", run["id"])
    assert result["status"] == "COMPLETE", result["error"]
    assert {x["document_key"] for x in result["extractions"]} == {"A", "B"}
    assert len(result["timeline"]) == 2
    assert len(result["findings"]) == 1
    assert [x["verdict"] for x in result["verifications"]] == ["challenged", "confirmed"]
    assert len(result["rulings"]) == 1
    assert len(result["email_drafts"]) == 1
    assert result["email_drafts"][0]["status"] == "DRAFT"
    assert "Source citations:" in result["email_drafts"][0]["body"]
    assert len(result["scenarios"]) == 1
    assert result["scenarios"][0]["exposure_amount"] is None
    assert any(x["from"] == "Odin" and x["to"] == "Loki" for x in result["messages"])
    calls = len(model.calls)
    execute_run(store, "org", run["id"], model)
    assert len(model.calls) == calls
    with sqlite3.connect(str(store.path) + ".langgraph.sqlite3") as db:
        assert db.execute("SELECT count(*) FROM checkpoints").fetchone()[0] > 0


def test_resume_does_not_repeat_completed_thor_call(tmp_path):
    store = Store(tmp_path / "odin.sqlite3")
    store.migrate()
    upsert_document(store, "org", "A", "Agreement", "Section 1. Payment\nCustomer shall pay $500 on 2027-03-15.\n", "test")
    run = start_run(store, "org", ["A"])

    class InterruptedModel(DebateModel):
        interrupted = False

        def _call(self, prompt, model, limit):
            if "You are Loki, adversarial" in prompt and not self.interrupted:
                self.interrupted = True
                raise KeyboardInterrupt("simulated process stop")
            if "You are Loki, adversarial" in prompt:
                self.calls.append(prompt)
                return '{"findings":[]}'
            return super()._call(prompt, model, limit)

    model = InterruptedModel()
    with pytest.raises(KeyboardInterrupt):
        execute_run(store, "org", run["id"], model)
    assert run_view(store, "org", run["id"])["status"] == "RUNNING"
    before = [item["id"] for item in run_view(store, "org", run["id"])["extractions"]]
    assert before
    execute_run(store, "org", run["id"], model)
    assert run_view(store, "org", run["id"])["status"] == "COMPLETE"
    assert [item["id"] for item in run_view(store, "org", run["id"])["extractions"]] == before


def test_exported_graph_matches_compiled_topology(tmp_path):
    graph = build_graph(Store(tmp_path / "odin.sqlite3"), "org", "diagram", DebateModel())
    exported = (Path(__file__).resolve().parents[1] / "docs" / "graph.mmd").read_text(encoding="utf-8")
    assert graph.get_graph(xray=True).draw_mermaid() == exported
    for node in ("thor", "loki", "thor_clarify", "heimdall_2", "odin_router", "loki_rebut", "tyr", "completeness_gate"):
        assert node in exported


def test_checkpoint_loop_excludes_future_events(tmp_path):
    store = Store(tmp_path / "odin.sqlite3")
    store.migrate()
    upsert_document(store, "org", "A", "Agreement", "Section 1. Payment\nCustomer shall pay $500 on 2027-03-15.\n", "test")
    add_event(store, "org", OperationalEvent.model_validate({
        "event_id": "E-1", "timestamp": "2027-05-01T00:00:00Z", "channel": "email",
        "from": "vendor@example.com", "to": "customer@example.com",
        "subject": "Payment", "body": "Payment event recorded",
    }))
    run = start_run(store, "org", ["A"], ["2027-03-15", "2027-06-01"])
    model = DebateModel()
    execute_run(store, "org", run["id"], model)
    result = run_view(store, "org", run["id"])
    assert result["status"] == "COMPLETE", result["error"]
    assert {s["clock_t"] for s in result["scenarios"]} == {"2027-03-15", "2027-06-01"}
    assert {v["clock_t"] for v in result["verifications"]} == {"2027-03-15", "2027-06-01"}
    checks = [prompt for prompt in model.calls if "You are Heimdall" in prompt]
    assert "E-1" not in checks[0]
    assert "E-1" in checks[-1]
