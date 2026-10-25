-- Migration 008: RAG chunk store with FTS5 (BM25 sparse) + vector slot (dense)
-- Hybrid search = BM25 rank + cosine similarity via RRF fusion

CREATE TABLE IF NOT EXISTS rag_chunks (
    id            TEXT PRIMARY KEY,
    owner_id      TEXT NOT NULL,
    document_key  TEXT NOT NULL,
    chunk_index   INTEGER NOT NULL,
    token_count   INTEGER NOT NULL,       -- approx tokens in this chunk
    text          TEXT NOT NULL,          -- raw chunk text (carried clause heading)
    embedding     BLOB,                   -- float32 LE bytes, NULL until embedded
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS rag_chunks_owner_doc ON rag_chunks(owner_id, document_key);

-- FTS5 table for BM25 sparse retrieval
CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
    id UNINDEXED,
    owner_id UNINDEXED,
    document_key UNINDEXED,
    text,
    content=rag_chunks,
    content_rowid=rowid
);

-- Trigger to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS rag_chunks_fts_insert AFTER INSERT ON rag_chunks BEGIN
    INSERT INTO rag_chunks_fts(rowid, id, owner_id, document_key, text)
    VALUES (new.rowid, new.id, new.owner_id, new.document_key, new.text);
END;

CREATE TRIGGER IF NOT EXISTS rag_chunks_fts_delete AFTER DELETE ON rag_chunks BEGIN
    INSERT INTO rag_chunks_fts(rag_chunks_fts, rowid, id, owner_id, document_key, text)
    VALUES ('delete', old.rowid, old.id, old.owner_id, old.document_key, old.text);
END;

-- RAG eval results per run
CREATE TABLE IF NOT EXISTS rag_eval (
    id            TEXT PRIMARY KEY,
    owner_id      TEXT NOT NULL,
    run_id        TEXT NOT NULL,
    chunk_id      TEXT NOT NULL,
    query         TEXT NOT NULL,
    retrieved_ids TEXT NOT NULL,          -- JSON array of chunk ids returned
    faithfulness  REAL,                   -- 0-1: answer grounded in retrieved context
    context_precision REAL,               -- 0-1: fraction of retrieved chunks that are relevant
    context_recall    REAL,               -- 0-1: fraction of relevant chunks retrieved
    answer_relevance  REAL,               -- 0-1: answer addresses the query
    created_at    TEXT NOT NULL
);

PRAGMA user_version=8;
