"""
Migrate all data to the new demo org (48bb8512-ace0-4ee5-a8a6-6965bac7939a)
"""
import sqlite3, uuid, json
from datetime import datetime, timezone

DB_PATH = 'data/ragnarok.sqlite3'
LOCAL_OWNER = 'local-owner'
ORG_ID = '48bb8512-ace0-4ee5-a8a6-6965bac7939a'  # Ragnarok Demo (demo@ragnarok.local)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

def now():
    return datetime.now(timezone.utc).isoformat()

# 1. Copy documents
docs = conn.execute("SELECT * FROM documents WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
print(f"Copying {len(docs)} documents to demo org...")
for doc in docs:
    existing = conn.execute("SELECT id FROM documents WHERE owner_id=? AND document_key=?", (ORG_ID, doc['document_key'])).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO documents(id, owner_id, document_key, title, content, content_sha256, source, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), ORG_ID, doc['document_key'], doc['title'], doc['content'], doc['content_sha256'], doc['source'] or 'migration', doc['created_at'], doc['updated_at'])
        )
        print(f"  + {doc['document_key']}")

# 2. Copy rag_chunks
chunks = conn.execute("SELECT * FROM rag_chunks WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
print(f"\nCopying {len(chunks)} rag_chunks...")
for c in chunks:
    existing = conn.execute("SELECT id FROM rag_chunks WHERE owner_id=? AND document_key=? AND chunk_index=?", (ORG_ID, c['document_key'], c['chunk_index'])).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO rag_chunks(id, owner_id, document_key, chunk_index, token_count, text, embedding, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), ORG_ID, c['document_key'], c['chunk_index'], c['token_count'], c['text'], c['embedding'], c['created_at'])
        )

# 3. Copy operational events
events = conn.execute("SELECT * FROM operational_events WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
print(f"\nCopying {len(events)} operational_events...")
for e in events:
    existing = conn.execute("SELECT event_id FROM operational_events WHERE owner_id=? AND event_id=?", (ORG_ID, e['event_id'])).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO operational_events(id, owner_id, event_id, occurred_at, channel, sender, recipient, subject, body, content_sha256, source, imported_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), ORG_ID, e['event_id'], e['occurred_at'], e['channel'], e['sender'], e['recipient'], e['subject'], e['body'], e['content_sha256'], e['source'], e['imported_at'])
        )

conn.commit()
conn.close()
print("\nDemo org migration complete!")
print(f"Org: {ORG_ID}")
