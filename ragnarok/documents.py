"""Local source-text storage and exact-substring citation checks."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import uuid
from .store import Store, now


MAX_TEXT_BYTES = 2_000_000
HEADING = re.compile(r"(?im)^\s*((?:section\s+[A-Z0-9.]+|§\s*\d+(?:\.\d+)*|\d+(?:\.\d+)+)\b[^\r\n]*)")


def _heading_at(content: str, offset: int) -> str | None:
    heading = None
    for match in HEADING.finditer(content):
        if match.start() > offset:
            break
        heading = match.group(1).strip()
    return heading


def upsert_document(store: Store, owner_id: str, key: str, title: str, content: str, source: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", key):
        raise ValueError("Document key must be 1-80 letters, digits, dots, dashes, or underscores")
    if not 1 <= len(title) <= 200:
        raise ValueError("Document title must be 1-200 characters")
    if not content or len(content.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("Document text must be 1 byte to 2 MB")
    digest = sha256(content.encode("utf-8")).hexdigest()
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT id,content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (owner_id, key)).fetchone()
        if prior:
            if prior["content_sha256"] != digest:
                db.execute("UPDATE documents SET title=?,content=?,content_sha256=?,source=?,updated_at=? WHERE id=? AND owner_id=?", (title, content, digest, source, now(), prior["id"], owner_id))
            document_id = prior["id"]
        else:
            document_id = str(uuid.uuid4())
            db.execute("INSERT INTO documents(id,owner_id,document_key,title,content,content_sha256,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (document_id, owner_id, key, title, content, digest, source, now(), now()))
        Store.audit(db, owner_id, "document.upsert", document_id, "allowed")
        return dict(db.execute("SELECT id,document_key,title,content_sha256,source,created_at,updated_at FROM documents WHERE id=? AND owner_id=?", (document_id, owner_id)).fetchone())


def search_documents(db: sqlite3.Connection, owner_id: str, query: str, limit: int = 20) -> list[dict]:
    if not query or len(query) > 200:
        raise ValueError("Search text must be 1-200 characters")
    rows = db.execute("SELECT document_key,title,content,content_sha256 FROM documents WHERE owner_id=? ORDER BY document_key", (owner_id,)).fetchall()
    results = []
    for row in rows:
        content = row["content"]
        match = re.search(re.escape(query), content, re.IGNORECASE)
        if match:
            offset = match.start()
            start = max(0, offset - 80)
            end = min(len(content), match.end() + 80)
            results.append({"document_key": row["document_key"], "title": row["title"], "content_sha256": row["content_sha256"], "offset": offset, "snippet": content[start:end], "heading": _heading_at(content, offset)})
            if len(results) >= limit:
                break
    return results


def verify_citation(db: sqlite3.Connection, owner_id: str, key: str, clause_ref: str, quote: str) -> dict:
    row = db.execute("SELECT content,content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (owner_id, key)).fetchone()
    if row is None:
        raise LookupError("Document not found")
    if not 1 <= len(quote) <= 1000 or not 1 <= len(clause_ref) <= 100:
        raise ValueError("Quote and clause reference must be non-empty and bounded")
    offset = row["content"].find(quote)
    heading = _heading_at(row["content"], offset) if offset >= 0 else None
    normalized_ref = re.sub(r"\s+", " ", clause_ref).strip().casefold()
    same_heading = offset >= 0 and _heading_at(row["content"], offset + len(quote) - 1) == heading
    heading_match = bool(heading and same_heading and heading.casefold().startswith(normalized_ref))
    return {"verified": offset >= 0 and heading_match, "quote_exact": offset >= 0, "heading_match": heading_match, "heading": heading, "offset": offset if offset >= 0 else None, "content_sha256": row["content_sha256"]}


def import_odin_bundle(store: Store, owner_id: str, bundle: Path) -> list[dict]:
    root = bundle.resolve(strict=True)
    manifest_path = (root / "manifest.json").resolve(strict=True)
    if not manifest_path.is_relative_to(root):
        raise ValueError("Manifest path escapes the bundle")
    if manifest_path.stat().st_size > 100_000:
        raise ValueError("Manifest exceeds size limit")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("files"), list) or len(manifest["files"]) > 100:
        raise ValueError("Manifest must contain at most 100 files")
    imported = []
    for entry in manifest["files"]:
        relative = Path(entry["path"])
        if not relative.parts or relative.suffix.lower() != ".txt" or relative.parts[0] not in {"contracts", "company"}:
            continue
        candidate = (root / relative).resolve(strict=True)
        if not candidate.is_relative_to(root):
            raise ValueError("Manifest path escapes the bundle")
        if candidate.stat().st_size > MAX_TEXT_BYTES:
            raise ValueError(f"Document exceeds size limit: {relative}")
        key = candidate.stem if relative.parts[0] == "contracts" else "company-context"
        imported.append(upsert_document(store, owner_id, key, entry["title"], candidate.read_text(encoding="utf-8"), f"bundle:{relative.as_posix()}"))
    return imported
