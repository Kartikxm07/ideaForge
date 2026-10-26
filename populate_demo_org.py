"""
Full data population script:
1. Ensure all docs are in demo org
2. Copy rag_chunks from local-owner to demo org
3. Run a full fresh agent run against demo org with all docs
4. Mark the run COMPLETE
"""
import sys, json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = 'data/ragnarok.sqlite3'
LOCAL_OWNER = 'local-owner'
DEMO_ORG = '48bb8512-ace0-4ee5-a8a6-6965bac7939a'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

def now():
    return datetime.now(timezone.utc).isoformat()

# === Step 1: Count docs per owner ===
docs_local = conn.execute("SELECT document_key, length(content) as l FROM documents WHERE owner_id=? ORDER BY document_key", (LOCAL_OWNER,)).fetchall()
docs_demo = conn.execute("SELECT document_key FROM documents WHERE owner_id=? ORDER BY document_key", (DEMO_ORG,)).fetchall()
print(f"Local-owner docs: {len(docs_local)}")
print(f"Demo-org docs: {len(docs_demo)}")
local_keys = {r['document_key'] for r in docs_local}
demo_keys = {r['document_key'] for r in docs_demo}
missing_in_demo = local_keys - demo_keys
print(f"Missing in demo: {missing_in_demo}")

# === Step 2: Migrate any missing docs ===
for doc in docs_local:
    key = doc['document_key']
    if key not in demo_keys:
        row = conn.execute("SELECT * FROM documents WHERE owner_id=? AND document_key=?", (LOCAL_OWNER, key)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO documents(id, owner_id, document_key, title, content, content_sha256, source, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), DEMO_ORG, row['document_key'], row['title'], row['content'], row['content_sha256'], row['source'] or 'migration', row['created_at'], now())
        )
        print(f"  + Migrated doc: {key}")
conn.commit()

# === Step 3: Migrate rag_chunks ===
chunks_local = conn.execute("SELECT * FROM rag_chunks WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
chunks_demo_count = conn.execute("SELECT count(*) as cnt FROM rag_chunks WHERE owner_id=?", (DEMO_ORG,)).fetchone()['cnt']
print(f"\nLocal-owner rag_chunks: {len(chunks_local)}")
print(f"Demo-org rag_chunks before migration: {chunks_demo_count}")

migrated = 0
for c in chunks_local:
    existing = conn.execute("SELECT id FROM rag_chunks WHERE owner_id=? AND document_key=? AND chunk_index=?",
                            (DEMO_ORG, c['document_key'], c['chunk_index'])).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO rag_chunks(id, owner_id, document_key, chunk_index, token_count, text, embedding, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), DEMO_ORG, c['document_key'], c['chunk_index'], c['token_count'], c['text'], c['embedding'], c['created_at'])
        )
        migrated += 1
conn.commit()
print(f"Migrated {migrated} new rag_chunks to demo org")

final_count = conn.execute("SELECT count(*) as cnt FROM rag_chunks WHERE owner_id=?", (DEMO_ORG,)).fetchone()['cnt']
print(f"Demo-org rag_chunks after migration: {final_count}")

# === Step 4: Check operational events for demo org ===
events_local = conn.execute("SELECT count(*) as cnt FROM operational_events WHERE owner_id=?", (LOCAL_OWNER,)).fetchone()['cnt']
events_demo = conn.execute("SELECT count(*) as cnt FROM operational_events WHERE owner_id=?", (DEMO_ORG,)).fetchone()['cnt']
print(f"\nOperational events: local={events_local}, demo={events_demo}")

if events_local > events_demo:
    all_events = conn.execute("SELECT * FROM operational_events WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
    ev_migrated = 0
    for e in all_events:
        ex = conn.execute("SELECT id FROM operational_events WHERE owner_id=? AND event_id=?", (DEMO_ORG, e['event_id'])).fetchone()
        if not ex:
            conn.execute(
                "INSERT INTO operational_events(id, owner_id, event_id, occurred_at, channel, sender, recipient, subject, body, content_sha256, source, imported_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), DEMO_ORG, e['event_id'], e['occurred_at'], e['channel'], e['sender'], e['recipient'], e['subject'], e['body'], e['content_sha256'], e['source'], e['imported_at'])
            )
            ev_migrated += 1
    conn.commit()
    print(f"Migrated {ev_migrated} operational events to demo org")

# === Summary ===
docs_final = conn.execute("SELECT document_key FROM documents WHERE owner_id=? ORDER BY document_key", (DEMO_ORG,)).fetchall()
print(f"\n=== FINAL DEMO ORG SUMMARY ===")
print(f"Documents: {[r['document_key'] for r in docs_final]}")
print(f"RAG Chunks: {conn.execute('SELECT count(*) FROM rag_chunks WHERE owner_id=?', (DEMO_ORG,)).fetchone()[0]}")
print(f"Events: {conn.execute('SELECT count(*) FROM operational_events WHERE owner_id=?', (DEMO_ORG,)).fetchone()[0]}")

conn.close()
print("\nDone! Ready to trigger a fresh agent run.")
