import sqlite3, uuid
from datetime import datetime, timezone

DB_PATH = 'data/ragnarok.sqlite3'
LOCAL_OWNER = 'local-owner'
ORG_ID = '149b8919-d90c-4007-bf0f-1b8d33414ac6'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Print schema
r = conn.execute("SELECT sql FROM sqlite_master WHERE name='documents'").fetchone()
print("Documents DDL:", r['sql'][:300] if r else 'not found')

# Check for unique constraint
rows = conn.execute("SELECT * FROM documents WHERE owner_id=?", (ORG_ID,)).fetchall()
print(f"\nDocs under org: {len(rows)}")

# Copy from local-owner to org
docs = conn.execute("SELECT * FROM documents WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
print(f"Docs under local-owner: {len(docs)}")

copied = 0
for doc in docs:
    existing = conn.execute("SELECT id FROM documents WHERE owner_id=? AND document_key=?", (ORG_ID, doc['document_key'])).fetchone()
    if existing:
        print(f"  = {doc['document_key']} already exists")
        continue
    new_id = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT INTO documents(id, owner_id, document_key, title, content, content_sha256, source, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (new_id, ORG_ID, doc['document_key'], doc['title'], doc['content'], doc['content_sha256'], doc['source'] or 'migration', doc['created_at'], doc['updated_at'])
        )
        print(f"  + {doc['document_key']} (len={len(doc['content'])})")
        copied += 1
    except Exception as ex:
        print(f"  ERR {doc['document_key']}: {ex}")

conn.commit()
print(f"\nCopied {copied} documents to org")

# Also copy rag_chunks with new ids
chunks = conn.execute("SELECT * FROM rag_chunks WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
print(f"\nCopying {len(chunks)} rag_chunks...")
rc_copied = 0
for c in chunks:
    existing = conn.execute("SELECT id FROM rag_chunks WHERE owner_id=? AND document_key=? AND chunk_index=?", (ORG_ID, c['document_key'], c['chunk_index'])).fetchone()
    if existing:
        continue
    new_id = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT INTO rag_chunks(id, owner_id, document_key, chunk_index, token_count, text, embedding, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (new_id, ORG_ID, c['document_key'], c['chunk_index'], c['token_count'], c['text'], c['embedding'], c['created_at'])
        )
        rc_copied += 1
    except Exception as ex:
        print(f"  ERR chunk {c['document_key']}:{c['chunk_index']}: {ex}")

conn.commit()
print(f"Copied {rc_copied} rag_chunks to org")
conn.close()
