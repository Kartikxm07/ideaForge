"""
thor_agent.storage
──────────────────
Storage layer for Thor Sub-Agent:
- SQLite table 'odin_chunks' storing clause chunks, PDF page mappings, bounding rects, and character offsets.
- SQLite table 'thor_facts' storing extracted facts with verified/repaired/rejected status.
- Numpy vector matrix saved on disk for similarity search and position indexing.
Pinecone/Chroma can replace this class with zero changes to Thor workers.
"""

from __future__ import annotations
import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class ChunkStorage:
    def __init__(self, db_path: Optional[str] = None, vector_path: Optional[str] = None, embedding_dim: int = 128):
        base_dir = Path(__file__).resolve().parent
        self.db_path = Path(db_path) if db_path else base_dir / "odin_chunks.db"
        self.vector_path = Path(vector_path) if vector_path else base_dir / "odin_vectors.npy"
        self.meta_path = Path(vector_path).with_suffix(".meta.json") if vector_path else base_dir / "odin_vectors_meta.json"
        self.embedding_dim = embedding_dim
        self._init_db()
        self._vectors: List[np.ndarray] = []
        self._row_ids: List[int] = []
        self._load_vectors()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS odin_chunks (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE NOT NULL,
                document_id TEXT NOT NULL,
                clause_ref TEXT,
                page_num INTEGER DEFAULT 1,
                char_start INTEGER DEFAULT 0,
                char_end INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                text TEXT NOT NULL,
                rects_json TEXT DEFAULT '[]',
                source_type TEXT DEFAULT 'contract',
                metadata_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS thor_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_type TEXT NOT NULL,
                document_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                quote TEXT NOT NULL,
                confidence REAL DEFAULT 0.9,
                value TEXT,
                status TEXT DEFAULT 'verified',
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()

    def clear(self):
        """Reset storage for fresh run."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM odin_chunks;")
            conn.execute("DELETE FROM thor_facts;")
            conn.commit()
        self._vectors = []
        self._row_ids = []
        if self.vector_path.exists():
            try:
                self.vector_path.unlink()
            except Exception:
                pass
        if self.meta_path.exists():
            try:
                self.meta_path.unlink()
            except Exception:
                pass

    def _embed_text(self, text: str) -> np.ndarray:
        """
        Deterministic lightweight semantic embedding:
        Combines hashed n-gram bag-of-words and lexical projections.
        Guarantees offline execution without GPU or API limits.
        """
        words = text.lower().split()
        vec = np.zeros(self.embedding_dim, dtype=np.float32)
        if not words:
            return vec
        for i, w in enumerate(words):
            h = hash(w)
            idx = abs(h) % self.embedding_dim
            sign = 1.0 if (h % 2 == 0) else -1.0
            vec[idx] += sign * (1.0 / (1.0 + math.log(1 + i)))
            if len(w) >= 3:
                for j in range(len(w) - 2):
                    trigram = w[j:j+3]
                    h_tri = hash(trigram)
                    idx_tri = abs(h_tri) % self.embedding_dim
                    vec[idx_tri] += 0.5 * (1.0 if (h_tri % 2 == 0) else -1.0)
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec

    def _load_vectors(self):
        if self.vector_path.exists() and self.meta_path.exists():
            try:
                matrix = np.load(str(self.vector_path))
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self._row_ids = json.load(f)
                self._vectors = [matrix[i] for i in range(len(matrix))]
            except Exception:
                self._vectors = []
                self._row_ids = []

    def _save_vectors(self):
        if self._vectors:
            matrix = np.vstack(self._vectors).astype(np.float32)
            np.save(str(self.vector_path), matrix)
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(self._row_ids, f)

    def store_chunk(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        clause_ref: Optional[str] = None,
        page_num: int = 1,
        char_start: int = 0,
        char_end: int = 0,
        token_count: int = 0,
        rects: Optional[List[List[float]]] = None,
        source_type: str = "contract",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store a chunk and return stored position descriptor.
        """
        if token_count <= 0:
            token_count = max(1, math.ceil(len(text) / 4.0))
        rects_json = json.dumps(rects or [])
        meta_json = json.dumps(metadata or {})

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO odin_chunks
                (chunk_id, document_id, clause_ref, page_num, char_start, char_end, token_count, text, rects_json, source_type, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                document_id=excluded.document_id,
                clause_ref=excluded.clause_ref,
                page_num=excluded.page_num,
                char_start=excluded.char_start,
                char_end=excluded.char_end,
                token_count=excluded.token_count,
                text=excluded.text,
                rects_json=excluded.rects_json,
                source_type=excluded.source_type,
                metadata_json=excluded.metadata_json
            """, (chunk_id, document_id, clause_ref, page_num, char_start, char_end, token_count, text, rects_json, source_type, meta_json))
            conn.commit()

            cur.execute("SELECT row_id FROM odin_chunks WHERE chunk_id = ?", (chunk_id,))
            row = cur.fetchone()
            row_id = row["row_id"] if row else 1

        # Update vector matrix
        vec = self._embed_text(text)
        if row_id in self._row_ids:
            idx = self._row_ids.index(row_id)
            self._vectors[idx] = vec
        else:
            self._row_ids.append(row_id)
            self._vectors.append(vec)
        self._save_vectors()

        # Stored position
        return {
            "collection": "odin_chunks",
            "row_id": row_id,
            "chunk_id": chunk_id,
            "document_id": document_id,
            "clause_ref": clause_ref or "",
            "page_num": page_num,
            "char_offsets": [char_start, char_end],
            "token_count": token_count,
            "rects": rects or [],
            "source_type": source_type,
        }

    def store_fact(
        self,
        fact_type: str,
        document_id: str,
        chunk_id: str,
        quote: str,
        confidence: float = 0.9,
        value: Optional[str] = None,
        status: str = "verified",
        explanation: Optional[str] = None,
    ) -> int:
        """
        Store an extracted fact. If status is rejected, caller should not call this.
        """
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO thor_facts (fact_type, document_id, chunk_id, quote, confidence, value, status, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (fact_type, document_id, chunk_id, quote, confidence, value or "", status, explanation or ""))
            conn.commit()
            return cur.lastrowid

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM odin_chunks WHERE chunk_id = ?", (chunk_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def get_chunk_by_row(self, row_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM odin_chunks WHERE row_id = ?", (row_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM odin_chunks ORDER BY row_id ASC")
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_all_facts(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM thor_facts ORDER BY id ASC")
            return [dict(r) for r in cur.fetchall()]

    def search_similarity(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self._vectors:
            return []
        q_vec = self._embed_text(query)
        matrix = np.vstack(self._vectors)
        scores = np.dot(matrix, q_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            row_id = self._row_ids[idx]
            chunk = self.get_chunk_by_row(row_id)
            if chunk:
                chunk["score"] = float(scores[idx])
                results.append(chunk)
        return results

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["rects"] = json.loads(d.get("rects_json") or "[]")
        except Exception:
            d["rects"] = []
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        return d
