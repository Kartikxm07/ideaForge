"""Human review remains scoped to the current organization and ruling."""

import asyncio

import httpx

from ragnarok.agents import _save
from ragnarok.api import create_app
from ragnarok.config import Settings
from ragnarok.store import Store


def test_review_queue_and_decision_round_trip(tmp_path):
    database = tmp_path / "review.sqlite3"
    app = create_app(Settings("a" * 40, "local", database, "", "unused"))
    store = Store(database)

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://local") as reviewer:
            registered = await reviewer.post("/api/v1/auth/register", json={
                "email": "reviewer@example.test", "password": "a-long-test-password",
                "name": "Reviewer", "organization": "Review Org", "terms": True,
            })
            assert registered.status_code == 201
            session = (await reviewer.get("/api/v1/auth/session")).json()
            org = session["organization_id"]
            with store.connect() as db:
                run = _save(db, org, "agent-run", {
                    "status": "COMPLETE", "document_keys": [], "checkpoints": [],
                    "error": None, "started_at": "2026-10-26T00:00:00Z",
                })
                finding = _save(db, org, "agent-finding", {
                    "run_id": run["id"], "claim": "Payment date needs review", "citations": [],
                })
                ruling = _save(db, org, "agent-ruling", {
                    "run_id": run["id"], "finding_id": finding["id"],
                    "outcome": "needs_review", "rationale": "Ambiguous clause",
                    "citations": [],
                })
                rejected = _save(db, org, "agent-ruling", {
                    "run_id": run["id"], "finding_id": finding["id"],
                    "outcome": "rejected", "rationale": "Unsupported", "citations": [],
                })

            base = f"/api/v1/workspace/agents/runs/{run['id']}/review-questions"
            queue = await reviewer.get(base)
            assert queue.status_code == 200
            assert queue.json()["pending"] == 1
            assert queue.json()["questions"][0]["finding_claim"] == "Payment date needs review"
            answer_url = f"{base}/{ruling['id']}/answer"
            assert (await reviewer.post(answer_url, json={"answer": "   ", "decision": "Reject"})).status_code == 422
            saved = await reviewer.post(answer_url, json={
                "answer": "The source does not establish the due date.", "decision": "Reject",
            })
            assert saved.status_code == 201
            resolved = (await reviewer.get(base)).json()
            assert resolved["pending"] == 0
            assert resolved["questions"][0]["decision"] == "Reject"
            assert resolved["questions"][0]["answer"] == "The source does not establish the due date."
            assert (await reviewer.post(f"{base}/{rejected['id']}/answer", json={
                "answer": "Trying to approve a rejected ruling", "decision": "Approve",
            })).status_code == 422

            async with httpx.AsyncClient(transport=transport, base_url="http://local") as other:
                assert (await other.post("/api/v1/auth/register", json={
                    "email": "other@example.test", "password": "another-test-password",
                    "name": "Other User", "organization": "Other Org", "terms": True,
                })).status_code == 201
                assert (await other.get(base)).status_code == 404
                assert (await other.post(answer_url, json={
                    "answer": "Cross-org attempt", "decision": "Approve",
                })).status_code == 404

    asyncio.run(exercise())
