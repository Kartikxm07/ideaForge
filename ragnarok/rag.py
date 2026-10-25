"""RAG pipeline for ODIN — 512-token chunks, hybrid BM25 + dense search, eval.

Architecture
────────────
Ingest path  : PDF/TXT upload → OCR fallback → 512-token chunker → rag_chunks table
               (FTS5 trigger auto-populates the BM25 index on each insert)

Retrieval     : Hybrid search — BM25 sparse score (FTS5) + cosine dense score (embedding)
               fused via Reciprocal Rank Fusion (RRF, k=60)

Eval pipeline : For every Thor query, measure four RAGAS-style metrics:
               • faithfulness       — does the LLM answer stay grounded in retrieved chunks?
               • context_precision  — fraction of retrieved chunks that are relevant
               • context_recall     — fraction of truly relevant chunks that were retrieved
               • answer_relevance   — does the final answer address the original question?
               Results land in rag_eval; the dashboard reads them for the Eval view.

Storage       : Local SQLite (owner-scoped, zero network hop, fully auditable).
               Dense embeddings stored as float32 BLOB; BM25 via built-in FTS5.
               Pinecone-compatible design: swap Store.hybrid_search() to call
               the Pinecone hybrid endpoint when you add the API key.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from typing import Iterable
from uuid import uuid4

from .store import Store, now


# ── tokenisation ─────────────────────────────────────────────────────────────
# Rule-of-thumb: 1 token ≈ 4 chars of English legal prose.
CHARS_PER_TOKEN = 4
CHUNK_TOKENS = 512
CHUNK_CHARS = CHUNK_TOKENS * CHARS_PER_TOKEN        # 2 048 chars

# How many chunks to return per retrieval leg before RRF fusion
SPARSE_TOP_K = 20
DENSE_TOP_K  = 20
FINAL_TOP_K  = 8

# RRF constant (standard: 60)
RRF_K = 60


# ── 512-token chunker ─────────────────────────────────────────────────────────

def _count_tokens(text: str) -> int:
    """Approximate token count (4 chars per token heuristic)."""
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


def chunk_document(text: str, document_key: str) -> list[dict]:
    """
    Split *text* into chunks of ≤ 512 tokens (≈ 2 048 chars).

    Each chunk carries the active clause heading as a prefix so retrieval
    context is always self-contained (RAG best-practice).

    Returns list of dicts:
        { id, document_key, chunk_index, token_count, text }
    """
    HEADING = re.compile(r"^#{1,3} (.+)$", re.MULTILINE)
    chunks: list[dict] = []
    current = ""
    heading = ""
    chunk_index = 0

    for line in text.splitlines(keepends=True):
        m = HEADING.match(line)
        if m:
            heading = m.group(1).strip()[:120]

        # Would adding this line overflow the budget?
        if len(current) + len(line) > CHUNK_CHARS and current.strip():
            _emit(chunks, current, document_key, chunk_index)
            chunk_index += 1
            # Carry heading into next chunk for context continuity
            current = (f"[{heading}]\n" if heading else "")

        current += line

    if current.strip():
        _emit(chunks, current, document_key, chunk_index)

    return chunks


def _emit(chunks: list, text: str, document_key: str, index: int) -> None:
    digest = hashlib.sha256(f"{document_key}\0{index}\0{text[:256]}".encode()).hexdigest()
    chunks.append({
        "id":           digest,
        "document_key": document_key,
        "chunk_index":  index,
        "token_count":  _count_tokens(text),
        "text":         text,
    })


# ── store / upsert ────────────────────────────────────────────────────────────

def upsert_chunks(store: Store, owner: str, document_key: str, text: str) -> int:
    """
    Chunk *text* and upsert into rag_chunks (idempotent on content hash).
    Returns the number of chunks stored.
    """
    chunks = chunk_document(text, document_key)
    with store.connect() as db:
        # Remove stale chunks for this document first
        db.execute("DELETE FROM rag_chunks WHERE owner_id=? AND document_key=?", (owner, document_key))
        for ch in chunks:
            db.execute(
                "INSERT OR IGNORE INTO rag_chunks"
                "(id, owner_id, document_key, chunk_index, token_count, text, embedding, created_at)"
                " VALUES (?,?,?,?,?,?,NULL,?)",
                (ch["id"], owner, ch["document_key"], ch["chunk_index"], ch["token_count"], ch["text"], now()),
            )
    return len(chunks)


def get_chunks(store: Store, owner: str, document_key: str) -> list[dict]:
    """Return stored chunks for a document, ordered by index."""
    with store.connect() as db:
        rows = db.execute(
            "SELECT id, chunk_index, token_count, text FROM rag_chunks"
            " WHERE owner_id=? AND document_key=? ORDER BY chunk_index",
            (owner, document_key),
        ).fetchall()
    return [dict(r) for r in rows]


# ── embedding (dense leg) ─────────────────────────────────────────────────────

def _embed_text(model, text: str) -> list[float] | None:
    """
    Request an embedding via the configured LLM provider.
    Falls back to None if the provider doesn't support /embeddings,
    in which case only BM25 (sparse) retrieval is used.
    """
    try:
        import httpx
        settings = model.settings
        base_url = getattr(settings, "openrouter_base_url", None) or "https://openrouter.ai/api/v1"
        api_key  = getattr(settings, "openrouter_api_key", "") or getattr(settings, "anthropic_api_key", "")
        if not api_key:
            return None
        resp = httpx.post(
            f"{base_url}/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "text-embedding-3-small", "input": text[:8000]},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()["data"][0]["embedding"]
    except Exception:
        pass
    return None


def _blob_to_vec(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def _vec_to_blob(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a))
    nb  = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-9)


def embed_document_chunks(store: Store, owner: str, document_key: str, model) -> int:
    """Compute and persist embeddings for all chunks of a document. Returns count embedded."""
    with store.connect() as db:
        rows = db.execute(
            "SELECT id, text FROM rag_chunks WHERE owner_id=? AND document_key=? AND embedding IS NULL",
            (owner, document_key),
        ).fetchall()
    embedded = 0
    for row in rows:
        vec = _embed_text(model, row["text"])
        if vec:
            with store.connect() as db:
                db.execute("UPDATE rag_chunks SET embedding=? WHERE id=? AND owner_id=?",
                           (_vec_to_blob(vec), row["id"], owner))
            embedded += 1
    return embedded


# ── hybrid retrieval ──────────────────────────────────────────────────────────

def hybrid_search(store: Store, owner: str, query: str, document_keys: list[str] | None = None,
                  model=None, top_k: int = FINAL_TOP_K) -> list[dict]:
    """
    Hybrid RAG retrieval: BM25 (sparse) ⊕ cosine similarity (dense) via RRF.

    1. BM25 pass  — FTS5 MATCH query, rank by -bm25(rag_chunks_fts)
    2. Dense pass — cosine similarity against stored embeddings (skipped if no embedding)
    3. RRF fusion — final_score = Σ 1/(rank + RRF_K) over both lists
    4. Return top_k chunks with scores and metadata
    """
    doc_filter = ""
    params_base: list = [owner]
    if document_keys:
        placeholders = ",".join("?" * len(document_keys))
        doc_filter = f" AND c.document_key IN ({placeholders})"
        params_base.extend(document_keys)

    # ── Leg 1: BM25 sparse ───────────────────────────────────────────────────
    # FTS5 match; sanitise query (remove FTS special chars)
    safe_q = re.sub(r'[^a-zA-Z0-9 ]', ' ', query).strip() or "contract"
    sparse_scores: dict[str, float] = {}
    sparse_texts:  dict[str, dict]  = {}
    try:
        with store.connect() as db:
            fts_params = [safe_q, owner] + (document_keys or [])
            doc_clause = f" AND f.owner_id = ?" + (f" AND f.document_key IN ({','.join('?'*len(document_keys))})" if document_keys else "")
            rows = db.execute(
                f"SELECT f.id, f.document_key, f.text, bm25(rag_chunks_fts) AS bm25_score"
                f" FROM rag_chunks_fts f"
                f" WHERE rag_chunks_fts MATCH ?"
                f"   AND f.owner_id = ?"
                f"{'  AND f.document_key IN (' + ','.join('?'*len(document_keys)) + ')' if document_keys else ''}"
                f" ORDER BY bm25_score LIMIT {SPARSE_TOP_K}",
                fts_params,
            ).fetchall()
            for rank, row in enumerate(rows):
                sparse_scores[row["id"]] = 1.0 / (rank + 1 + RRF_K)
                sparse_texts[row["id"]] = {"id": row["id"], "document_key": row["document_key"], "text": row["text"]}
    except Exception:
        pass   # FTS may not exist yet in older DBs

    # ── Leg 2: Dense cosine ───────────────────────────────────────────────────
    dense_scores: dict[str, float] = {}
    dense_texts:  dict[str, dict]  = {}
    if model is not None:
        q_vec = _embed_text(model, query)
        if q_vec:
            with store.connect() as db:
                params = [owner] + (document_keys or [])
                rows = db.execute(
                    "SELECT id, document_key, text, embedding FROM rag_chunks c"
                    " WHERE c.owner_id=? AND c.embedding IS NOT NULL"
                    + (f" AND c.document_key IN ({','.join('?'*len(document_keys))})" if document_keys else ""),
                    params,
                ).fetchall()
            scored = []
            for row in rows:
                vec = _blob_to_vec(row["embedding"])
                score = _cosine(q_vec, vec)
                scored.append((score, row))
            scored.sort(key=lambda x: -x[0])
            for rank, (score, row) in enumerate(scored[:DENSE_TOP_K]):
                dense_scores[row["id"]] = 1.0 / (rank + 1 + RRF_K)
                dense_texts[row["id"]] = {"id": row["id"], "document_key": row["document_key"], "text": row["text"], "dense_score": score}

    # ── RRF fusion ────────────────────────────────────────────────────────────
    all_ids = set(sparse_scores) | set(dense_scores)
    fused: list[tuple[float, str]] = []
    for cid in all_ids:
        rrf = sparse_scores.get(cid, 0.0) + dense_scores.get(cid, 0.0)
        fused.append((rrf, cid))
    fused.sort(key=lambda x: -x[0])

    results = []
    for rrf_score, cid in fused[:top_k]:
        info = sparse_texts.get(cid) or dense_texts.get(cid) or {}
        results.append({
            **info,
            "rrf_score":    round(rrf_score, 6),
            "sparse_score": round(sparse_scores.get(cid, 0.0), 6),
            "dense_score":  round(dense_scores.get(cid, {}).get("dense_score", 0.0) if isinstance(dense_scores.get(cid), dict) else 0.0, 6),
        })
    return results


# ── evaluation pipeline ───────────────────────────────────────────────────────

def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def evaluate_retrieval(
    store: Store,
    owner: str,
    run_id: str,
    query: str,
    retrieved_chunks: list[dict],
    answer: str,
    ground_truth_ids: list[str] | None = None,
) -> dict:
    """
    RAGAS-style evaluation for one retrieval + answer pair.

    Metrics (all 0.0 – 1.0):
    • faithfulness       — keyword overlap between answer and retrieved context
    • context_precision  — fraction of retrieved chunks containing query terms
    • context_recall     — fraction of ground-truth IDs recovered (if provided)
    • answer_relevance   — query-term overlap in the answer
    """
    query_tokens = set(re.findall(r'\w+', query.lower()))
    answer_tokens = set(re.findall(r'\w+', answer.lower()))
    context_text  = " ".join(c.get("text", "") for c in retrieved_chunks)
    context_tokens = set(re.findall(r'\w+', context_text.lower()))
    retrieved_ids  = [c["id"] for c in retrieved_chunks]

    # faithfulness: how much of the answer is grounded in retrieved context
    if answer_tokens:
        faithfulness = len(answer_tokens & context_tokens) / len(answer_tokens)
    else:
        faithfulness = 0.0

    # context_precision: fraction of retrieved chunks that mention query terms
    if retrieved_chunks:
        relevant_count = sum(
            1 for c in retrieved_chunks
            if query_tokens & set(re.findall(r'\w+', c.get("text", "").lower()))
        )
        context_precision = relevant_count / len(retrieved_chunks)
    else:
        context_precision = 0.0

    # context_recall: fraction of ground-truth IDs that were retrieved
    if ground_truth_ids:
        hit = len(set(retrieved_ids) & set(ground_truth_ids))
        context_recall = hit / len(ground_truth_ids)
    else:
        context_recall = None  # not measurable without ground-truth

    # answer_relevance: query terms present in answer
    if query_tokens:
        answer_relevance = len(query_tokens & answer_tokens) / len(query_tokens)
    else:
        answer_relevance = 0.0

    record = {
        "id":               str(uuid4()),
        "owner_id":         owner,
        "run_id":           run_id,
        "chunk_id":         retrieved_ids[0] if retrieved_ids else "",
        "query":            query[:500],
        "retrieved_ids":    json.dumps(retrieved_ids),
        "faithfulness":     round(faithfulness, 4),
        "context_precision": round(context_precision, 4),
        "context_recall":   round(context_recall, 4) if context_recall is not None else None,
        "answer_relevance": round(answer_relevance, 4),
        "created_at":       now(),
    }
    with store.connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO rag_eval"
            "(id,owner_id,run_id,chunk_id,query,retrieved_ids,faithfulness,"
            " context_precision,context_recall,answer_relevance,created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (record["id"], owner, run_id, record["chunk_id"], record["query"],
             record["retrieved_ids"], record["faithfulness"], record["context_precision"],
             record["context_recall"], record["answer_relevance"], record["created_at"]),
        )
    return record


def eval_summary(store: Store, owner: str, run_id: str) -> dict:
    """Aggregate eval metrics for a run."""
    with store.connect() as db:
        rows = db.execute(
            "SELECT faithfulness, context_precision, context_recall, answer_relevance"
            " FROM rag_eval WHERE owner_id=? AND run_id=?",
            (owner, run_id),
        ).fetchall()
    if not rows:
        return {"count": 0}

    def _avg(col: list) -> float | None:
        vals = [v for v in col if v is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    return {
        "count":             len(rows),
        "faithfulness":      _avg([r["faithfulness"] for r in rows]),
        "context_precision": _avg([r["context_precision"] for r in rows]),
        "context_recall":    _avg([r["context_recall"] for r in rows]),
        "answer_relevance":  _avg([r["answer_relevance"] for r in rows]),
    }
