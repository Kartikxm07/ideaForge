"""Approval and idempotent Resend request checks without sending email."""
import asyncio

import httpx

from ragnarok.agents import _save
from ragnarok.api import create_app
from ragnarok.config import Settings
from ragnarok.email_delivery import EmailDeliveryError, send_approved_alert
from ragnarok.store import Store


def test_resend_requires_approval_and_uses_stable_idempotency_key(monkeypatch, tmp_path):
    settings = Settings("x" * 40, "owner", tmp_path / "db.sqlite3", "", "fake",
                        resend_api_key="test-key", resend_from_email="alerts@example.com")
    draft = {"id": "draft-1", "status": "DRAFT", "recipient": "owner@example.com",
             "subject": "ODIN alert", "body": "A cited risk needs review."}
    try:
        send_approved_alert(settings, draft)
        assert False, "unapproved draft must not send"
    except EmailDeliveryError:
        pass
    seen = []

    def fake_post(url, *, headers, json, timeout):
        seen.append((url, headers["Idempotency-Key"], json["to"]))
        return httpx.Response(200, json={"id": "email-123"})

    monkeypatch.setattr(httpx, "post", fake_post)
    draft["status"] = "APPROVED"
    assert send_approved_alert(settings, draft) == "email-123"
    assert seen == [("https://api.resend.com/emails", "odin-alert-draft-1", ["owner@example.com"])]


def test_workspace_email_draft_requires_explicit_approval(monkeypatch, tmp_path):
    async def exercise():
        settings = Settings("x" * 40, "local-owner", tmp_path / "db.sqlite3", "", "fake",
                            resend_api_key="test-key", resend_from_email="alerts@example.com")
        app = create_app(settings)
        store = Store(settings.db_path)
        calls = []

        def fake_send(_settings, draft):
            calls.append(draft["recipient"])
            return "resend-id"

        monkeypatch.setattr("ragnarok.workspace_api.send_approved_alert", fake_send)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/v1/auth/register", json={
                "email": "admin@example.com", "password": "very-long-password",
                "name": "Admin", "organization": "Test Co", "terms": True,
            })
            assert response.status_code == 201
            with store.connect() as db:
                org = db.execute("SELECT id FROM web_orgs").fetchone()[0]
                draft = _save(db, org, "agent-email-draft", {
                    "run_id": "run-1", "finding_id": "finding-1", "status": "DRAFT",
                    "recipient": None, "subject": "ODIN review alert", "body": "A cited contract risk needs human review.",
                })
            path = f"/api/v1/workspace/agents/email-drafts/{draft['id']}"
            assert (await client.post(path + "/send")).status_code == 409
            assert calls == []
            response = await client.post(path + "/approve", json={
                "recipient": "owner@example.com", "subject": "ODIN review alert",
                "body": "A cited contract risk needs human review.",
            })
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "APPROVED"
            response = await client.post(path + "/send")
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "SENT"
            assert calls == ["owner@example.com"]
            assert (await client.post(path + "/send")).status_code == 409

    asyncio.run(exercise())
