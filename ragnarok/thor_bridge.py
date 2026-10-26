"""Adapter between ODIN LangGraph runs and the standalone Thor sub-agent."""
from __future__ import annotations

from pathlib import Path
import json
import re

from thor_agent import ChunkStorage, ClauseChunker, PDFProcessor, ThorExtractor
from thor_agent.blockchain import connect, receipt, save_new, snapshot, submit


def run_dir(store_path: Path, run_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "-", run_id)[:100]
    root = Path(store_path).parent / "thor_runs" / safe
    root.mkdir(parents=True, exist_ok=True)
    return root



def evidence_db(store_path: Path, run_id: str) -> Path:
    return run_dir(store_path, run_id) / "evidence.sqlite3"


def anchor_paths(store_path: Path, run_id: str) -> dict[str, Path]:
    root = run_dir(store_path, run_id) / "anchor"
    return {name: root / f"{name}.json" for name in ("snapshot", "pending", "receipt")}


def prepare_anchor(store_path: Path, run_id: str) -> dict:
    paths = anchor_paths(store_path, run_id)
    bundle = snapshot(evidence_db(store_path, run_id))
    if paths["snapshot"].exists():
        saved = json.loads(paths["snapshot"].read_text(encoding="utf-8"))
        if saved["sha256"] != bundle["sha256"]:
            raise ValueError("Thor evidence changed after the anchor snapshot was prepared")
    else:
        save_new(paths["snapshot"], bundle)
    return {"run_id": run_id, "sha256": bundle["sha256"], "status": "PREPARED"}


def submit_anchor(store_path: Path, run_id: str, settings) -> dict:
    paths = anchor_paths(store_path, run_id)
    if paths["pending"].exists():
        record = json.loads(paths["pending"].read_text(encoding="utf-8"))
        return {key: value for key, value in record.items() if key != "raw_transaction"}
    prepared = prepare_anchor(store_path, run_id)
    bundle = json.loads(paths["snapshot"].read_text(encoding="utf-8"))
    web3 = connect(settings.thor_sepolia_rpc_url or None)
    result = submit(bundle, paths["pending"], web3,
                    settings.thor_testnet_private_key or None)
    result.pop("raw_transaction", None)
    return {**prepared, **result}


def verify_anchor_receipt(store_path: Path, run_id: str, settings) -> dict:
    paths = anchor_paths(store_path, run_id)
    if not paths["snapshot"].is_file() or not paths["pending"].is_file():
        raise ValueError("Prepare and submit the Thor evidence anchor first")
    bundle = json.loads(paths["snapshot"].read_text(encoding="utf-8"))
    record = json.loads(paths["pending"].read_text(encoding="utf-8"))
    result = receipt(bundle, record, connect(settings.thor_sepolia_rpc_url or None))
    if not paths["receipt"].exists():
        save_new(paths["receipt"], result)
    return result


def extract_with_thor(store_path: Path, run_id: str, document_key: str, title: str,
                      content: str, settings, emit=None) -> list[dict]:
    """Chunk, vectorize, extract, and verify one document using Thor itself."""
    root = run_dir(store_path, run_id)
    vector_key = re.sub(r"[^A-Za-z0-9_.-]", "-", document_key)[:80]
    storage = ChunkStorage(str(evidence_db(store_path, run_id)), str(root / f"{vector_key}.vectors.npy"))
    pack_dir = Path(__file__).resolve().parents[1] / "dataset" / "Pack" / "odin_dev_pack"
    processor = PDFProcessor(pack_dir=str(pack_dir))
    twin = pack_dir / "bundle" / "contracts" / f"{document_key}.pdf"
    chunks = ClauseChunker(processor).chunk_contract(
        content, document_key, twin_pdf=twin if twin.is_file() else None,
    )
    for number, chunk in enumerate(chunks, 1):
        storage.store_chunk(
            chunk_id=chunk.chunk_id, document_id=chunk.document_id,
            text=chunk.text, clause_ref=chunk.clause_ref,
            page_num=chunk.page_num, char_start=chunk.char_start,
            char_end=chunk.char_end, token_count=chunk.token_count,
            rects=chunk.rects, source_type=chunk.source_type,
            metadata={"title": title, "run_id": run_id},
        )
        if emit and (number == 1 or number == len(chunks) or number % 5 == 0):
            emit("chunk", {"document_key": document_key, "current": number,
                           "total": len(chunks), "chunk_id": chunk.chunk_id})
    api_key = getattr(settings, "openrouter_api_key", "")
    extractor = ThorExtractor(
        llm_base_url="https://openrouter.ai/api/v1" if api_key else None,
        llm_api_key=api_key or None,
        llm_model=getattr(settings, "model_heavy", "openai/gpt-oss-120b"),
    )
    facts = extractor.extract_facts_for_contract(document_key, content, chunks)
    if not facts:
        raw = extractor._regex_fallback(content, chunks)
        facts = [fact for item in raw
                 if (fact := extractor._verify_and_repair_quote(
                     item, document_key, chunks, is_fallback=True)) is not None]
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    results = []
    for fact in facts:
        if fact.status == "rejected" or fact.chunk_id not in by_id:
            continue
        storage.store_fact(
            fact_type=fact.fact_type, document_id=fact.document_id,
            chunk_id=fact.chunk_id, quote=fact.quote,
            confidence=fact.confidence, value=fact.value,
            status=fact.status, explanation=fact.explanation,
        )
        chunk = by_id[fact.chunk_id]
        results.append({
            "field": fact.fact_type, "value": fact.value,
            "confidence": fact.confidence, "ambiguity": None,
            "status": fact.status, "explanation": fact.explanation,
            "citation": {
                "document_key": document_key, "clause_ref": chunk.clause_ref,
                "quote": fact.quote, "offset": content.find(fact.quote),
                "page_num": chunk.page_num, "rects": chunk.rects,
                "chunk_id": chunk.chunk_id,
            },
        })
        if emit:
            emit("fact", {"document_key": document_key, "fact_type": fact.fact_type,
                          "chunk_id": fact.chunk_id, "status": fact.status,
                          "confidence": fact.confidence})
    return results
