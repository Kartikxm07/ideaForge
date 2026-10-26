"""Run the two PS-2 questions through the current FastAPI application."""
import asyncio
import json
from pathlib import Path

import httpx

from ragnarok.api import create_app
from ragnarok.config import Settings


QUESTIONS = [
    "Is Quillhub currently in default or material breach of any terms in the Harbor Retail agreement (B1), unrelated to service outages? Cite specific provisions and company records.",
    "On March 3, 2027, an unscheduled outage occurred (Event E-04). What was Quillhub's platform uptime percentage for March 2027, what financial credits does Quillhub owe its customers, and what credits can Quillhub recover from StratoNode?",
]


async def main() -> None:
    settings = Settings.from_env()
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    results = []
    async with httpx.AsyncClient(transport=transport, base_url="http://odin.local", timeout=180) as client:
        for question in QUESTIONS:
            response = await client.post(
                "/api/v1/workspace/trial/rag-ask",
                headers={"Authorization": f"Bearer {settings.api_token}"},
                json={"question": question, "send_email": False},
            )
            payload = response.json()
            results.append({"status_code": response.status_code, **payload})
            print(json.dumps({
                "status_code": response.status_code,
                "question": question,
                "answer": payload.get("answer"),
                "proofs": [(p.get("document_key"), p.get("chunk_id")) for p in payload.get("proofs", [])],
                "qa_id": payload.get("qa_id"),
            }, ensure_ascii=True), flush=True)
    output = Path("artifacts/ps2-judge-api-results.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
