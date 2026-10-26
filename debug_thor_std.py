"""
Debug: find exactly why Thor/STD fails with AttributeError.
Reproduce the exact error from the thor node.
"""
import sys, traceback, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from ragnarok.store import Store
from ragnarok.config import Settings
from ragnarok.rag import upsert_chunks

DB_PATH = 'data/ragnarok.sqlite3'
OWNER = '48bb8512-ace0-4ee5-a8a6-6965bac7939a'
DOC_ID = 'STD'
RUN_ID = 'debug-test-001'

store = Store(DB_PATH)
settings = Settings.from_env()

# Step 1: Load document
with store.connect() as db:
    row = db.execute("SELECT title,content,content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (OWNER, DOC_ID)).fetchone()

if not row:
    print(f"STD doc not found for demo org! Checking local-owner...")
    with store.connect() as db:
        row = db.execute("SELECT title,content,content_sha256 FROM documents WHERE document_key=? LIMIT 1", (DOC_ID,)).fetchone()

title = row['title']
content = row['content']
print(f"Step 1: Loaded STD doc, title={title}, len={len(content)}")

# Step 2: upsert_chunks
try:
    n_chunks = upsert_chunks(store, OWNER, DOC_ID, content)
    print(f"Step 2: upsert_chunks OK — {n_chunks} chunks")
except Exception as e:
    print(f"Step 2 FAILED: upsert_chunks error: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 3: extract_with_thor
print("\nStep 3: extract_with_thor ...")
try:
    from ragnarok.thor_bridge import extract_with_thor
    facts = extract_with_thor(store.path, RUN_ID, DOC_ID, title, content, settings)
    print(f"Step 3 OK: {len(facts)} facts extracted")
    for f in facts[:3]:
        print(f"  [{f['field']}] {f['value'][:80]}")
except Exception as e:
    print(f"Step 3 FAILED: {type(e).__name__}: {e}")
    traceback.print_exc()
