import asyncio
from io import BytesIO
import json

import httpx
from reportlab.pdfgen import canvas

from ragnarok.api import create_app
from ragnarok.config import Settings


def test_pdf_txt_jsonl_and_paste_uploads(tmp_path):
    async def exercise():
        settings = Settings("x" * 40, "local-owner", tmp_path / "workspace.sqlite3", "", "test")
        app = create_app(settings)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/v1/auth/register", json={"email": "upload@example.com", "password": "very-long-password", "name": "Upload User", "organization": "Test Co", "terms": True})
            assert response.status_code == 201

            text = b"Section 1. Payment\nThe Customer shall pay $500 under this agreement."
            response = await client.post("/api/v1/workspace/upload-file", files={"file": ("terms.txt", text, "text/plain")})
            assert response.status_code == 201, response.text
            assert response.json()["kind"] == "contract"
            source = await client.get("/api/v1/workspace/contracts/terms/source")
            assert source.content == text

            pdf = BytesIO()
            page = canvas.Canvas(pdf)
            page.drawString(72, 720, "Section 1. Payment")
            page.drawString(72, 700, "The Customer shall pay $500 under this agreement.")
            page.save()
            raw_pdf = pdf.getvalue()
            response = await client.post("/api/v1/workspace/upload-file", files={"file": ("vendor.pdf", raw_pdf, "application/pdf")})
            assert response.status_code == 201, response.text
            assert response.json()["pages"] == 1
            source = await client.get("/api/v1/workspace/contracts/vendor/source")
            assert source.content == raw_pdf
            detail = await client.get("/api/v1/workspace/contracts/vendor")
            assert "The Customer shall pay $500" in detail.json()["content"]
            assert "# Page 1" in detail.json()["content"]

            event = {"event_id": "E-01", "timestamp": "2027-03-01T10:00:00Z", "channel": "email", "from": "vendor@example.com", "to": "legal@example.com", "subject": "Notice", "body": "Service notice"}
            lines = json.dumps(event).encode() + b"\nnot-json\n"
            response = await client.post("/api/v1/workspace/upload-file", files={"file": ("events.jsonl", lines, "application/x-ndjson")})
            assert response.status_code == 201, response.text
            assert response.json()["kind"] == "events"
            assert response.json()["created"] == 1
            assert response.json()["quarantined"] == 1
            assert len((await client.get("/api/v1/workspace/events")).json()) == 1

            contract_line = json.dumps({"text": "Section 2. Renewal\nThe agreement shall renew on 2028-03-15."}).encode()
            response = await client.post("/api/v1/workspace/upload-file", files={"file": ("clauses.jsonl", contract_line, "application/x-ndjson")})
            assert response.status_code == 201, response.text
            assert response.json()["kind"] == "contract"
            assert "# Record 1" in (await client.get("/api/v1/workspace/contracts/clauses")).json()["content"]

            response = await client.post("/api/v1/workspace/upload", json={"document_key": "paste", "title": "Pasted agreement", "content": "Section 3. Notice\nThe Customer shall send written notice under this agreement."})
            assert response.status_code == 201, response.text
            assert (await client.get("/api/v1/workspace/contracts")).json()["total"] == 4

            response = await client.post("/api/v1/workspace/upload-file", files={"file": ("terminal.txt", b"athar@eth:~$ nping -p 80\nnping: bad option\n", "text/plain")})
            assert response.status_code == 422
            assert "not a contract" in response.json()["detail"]

    asyncio.run(exercise())
