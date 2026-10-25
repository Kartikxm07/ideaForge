"""
thor_agent.server
─────────────────
FastAPI web server for Thor Sub-Agent:
- Streams real-time updates via Server-Sent Events (SSE) into Box 1, Box 2, and Box 3.
- Delivers PDF page images with rendered highlight bounding boxes for the visual Proof Step.
- Provides raw PDF streaming for embedded browser PDF viewers.
- Serves live ui.html at http://localhost:8000.
"""

from __future__ import annotations
import asyncio
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .storage import ChunkStorage
from .ocr_pdf import PDFProcessor
from .thor import ThorAgent

logger = logging.getLogger("thor_agent.server")

app = FastAPI(title="Thor Sub-Agent", version="1.0.0", description="Autonomous Contract Intelligence & Evidence Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
storage = ChunkStorage()
pack_dir = os.environ.get("ODIN_PACK_DIR", r"C:\Users\athar\OneDrive\Desktop\ragnarork\dataset\Pack\odin_dev_pack")
pdf_processor = PDFProcessor(pack_dir=pack_dir)
thor_agent = ThorAgent(pack_dir=pack_dir, storage=storage)

# Event subscribers for live SSE streaming
subscribers: List[asyncio.Queue] = []
event_loop: Optional[asyncio.AbstractEventLoop] = None


def dispatch_event(event_type: str, data: Dict[str, Any]):
    """Thread-safe event broadcaster to all active SSE subscribers."""
    global event_loop
    payload = json.dumps({"event": event_type, "data": data})
    for q in list(subscribers):
        try:
            if event_loop and event_loop.is_running():
                event_loop.call_soon_threadsafe(q.put_nowait, payload)
            else:
                q.put_nowait(payload)
        except Exception:
            pass


# Wire Thor callbacks to SSE broadcaster
thor_agent.on_odin_fetch = lambda data: dispatch_event("odin_fetch", data)
thor_agent.on_thor_fact = lambda data: dispatch_event("thor_fact", data)
thor_agent.on_chunk_stored = lambda data: dispatch_event("chunk_stored", data)
thor_agent.on_progress = lambda data: dispatch_event("progress", data)


class VerifyQuoteRequest(BaseModel):
    quote: str
    chunk_id: str
    document_id: str


@app.on_event("startup")
async def startup_event():
    global event_loop
    event_loop = asyncio.get_running_loop()


@app.get("/", response_class=HTMLResponse)
async def get_ui():
    ui_path = Path(__file__).parent / "ui.html"
    if ui_path.exists():
        with open(ui_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Thor Sub-Agent Server</h1><p>ui.html not found</p>")


@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "agent": "Thor Sub-Agent",
        "pack_dir": str(thor_agent.pack_dir),
        "pack_exists": thor_agent.pack_dir.exists(),
        "llm_model": thor_agent.extractor.model,
        "llm_configured": bool(thor_agent.extractor.base_url and thor_agent.extractor.api_key),
        "pymupdf_available": True,
        "stored_chunks_count": len(storage.get_all_chunks()),
        "extracted_facts_count": len(storage.get_all_facts()),
    }


@app.post("/api/run")
async def trigger_run():
    """Trigger Thor analysis run in a background executor."""
    loop = asyncio.get_running_loop()
    summary = await loop.run_in_executor(None, thor_agent.run_analysis)
    return summary


@app.get("/api/stream")
async def sse_stream(request: Request):
    """Server-Sent Events endpoint streaming Box 1, Box 2, and Box 3 live."""
    queue = asyncio.Queue()
    subscribers.append(queue)

    async def event_generator():
        try:
            # Send initial keepalive & status
            yield {
                "event": "connected",
                "data": json.dumps({"status": "connected", "pack_dir": str(thor_agent.pack_dir)})
            }
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=20.0)
                    msg = json.loads(payload)
                    yield {
                        "event": msg.get("event", "message"),
                        "data": json.dumps(msg.get("data", {}))
                    }
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            if queue in subscribers:
                subscribers.remove(queue)

    return EventSourceResponse(event_generator())


@app.get("/api/chunks")
async def get_chunks():
    """Retrieve all stored chunks from SQLite."""
    return {"chunks": storage.get_all_chunks()}


@app.get("/api/facts")
async def get_facts():
    """Retrieve all extracted facts from SQLite."""
    return {"facts": storage.get_all_facts()}


@app.get("/api/chunk/{chunk_id}")
async def get_chunk_detail(chunk_id: str):
    """Get chunk detail including rects and stored position."""
    chunk = storage.get_chunk(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")
    return chunk


@app.get("/api/pdf_file")
async def get_pdf_file(doc: str = Query(..., description="Document stem or key, e.g. B1 or contracts/B1.txt")):
    """Streams raw PDF for embedded browser viewer or download."""
    twin_pdf = pdf_processor.find_twin_pdf(doc, base_pack_dir=thor_agent.pack_dir)
    if not twin_pdf or not twin_pdf.exists():
        raise HTTPException(status_code=404, detail=f"PDF twin for {doc} not found")
    return FileResponse(str(twin_pdf), media_type="application/pdf", filename=twin_pdf.name)


@app.get("/api/pdf_page")
async def get_pdf_page(
    doc: str = Query(..., description="Document ID or key, e.g. B1"),
    page: int = Query(1, description="1-indexed page number"),
    chunk_id: Optional[str] = Query(None, description="Optional chunk ID to highlight"),
    quote: Optional[str] = Query(None, description="Optional quote string to highlight"),
    format: str = Query("json", description="'json' for base64 or 'png' for raw image"),
):
    """
    Renders high-res PDF page with highlight bounding box drawn over the exact clause.
    """
    twin_pdf = pdf_processor.find_twin_pdf(doc, base_pack_dir=thor_agent.pack_dir)
    if not twin_pdf or not twin_pdf.exists():
        raise HTTPException(status_code=404, detail=f"Twin PDF for document '{doc}' not found")

    rects = []
    if chunk_id:
        c = storage.get_chunk(chunk_id)
        if c:
            rects = c.get("rects", [])
            if not quote:
                quote = c.get("text", "")

    if format == "png":
        png_bytes, _ = pdf_processor.render_highlighted_page(
            twin_pdf,
            page_num=page,
            rects=rects,
            quote_to_highlight=quote,
            dpi=150
        )
        if not png_bytes:
            raise HTTPException(status_code=500, detail="Failed to render PDF page")
        return Response(content=png_bytes, media_type="image/png")

    result = pdf_processor.render_page_base64(
        twin_pdf,
        page_num=page,
        rects=rects,
        quote_to_highlight=quote
    )
    result["pdf_filename"] = twin_pdf.name
    return result


@app.post("/api/verify_quote")
async def verify_quote(req: VerifyQuoteRequest):
    """Interactive quote verification endpoint."""
    target_chunk = storage.get_chunk(req.chunk_id)
    all_chunks = storage.get_all_chunks()
    doc_chunks = [c for c in all_chunks if c["document_id"] == req.document_id or Path(c["document_id"]).stem == Path(req.document_id).stem]

    clean_quote = " ".join(req.quote.strip().split()).lower()

    # 1. Check target chunk
    if target_chunk and clean_quote in " ".join(target_chunk["text"].split()).lower():
        return {
            "verified": True,
            "status": "verified",
            "chunk_id": req.chunk_id,
            "explanation": "Verbatim quote verified in target chunk."
        }

    # 2. Check other chunks (repair)
    for other in doc_chunks:
        if clean_quote in " ".join(other["text"].split()).lower():
            return {
                "verified": True,
                "status": "repaired",
                "chunk_id": other["chunk_id"],
                "explanation": f"Repaired: Quote belonged to {other['chunk_id']} instead of {req.chunk_id}."
            }

    # 3. Reject
    return {
        "verified": False,
        "status": "rejected",
        "chunk_id": None,
        "explanation": "Quote rejected: Fabricated or not found anywhere in document text."
    }
