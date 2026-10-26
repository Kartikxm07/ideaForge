import traceback
from pathlib import Path
from ragnarok.store import Store
from ragnarok.config import Settings
from ragnarok.thor_bridge import extract_with_thor

store = Store('data/ragnarok.sqlite3')
owner = '48bb8512-ace0-4ee5-a8a6-6965bac7939a'
doc_id = 'STD'

with store.connect() as db:
    row = db.execute("SELECT title, content, content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (owner, doc_id)).fetchone()
    if not row:
        print("Document not found for org, checking local-owner...")
        row = db.execute("SELECT title, content, content_sha256 FROM documents WHERE document_key=? LIMIT 1", (doc_id,)).fetchone()

if not row:
    print("Document STD not found in database!")
    exit(1)

title = row["title"]
content = row["content"]
print(f"Loaded {doc_id}: title={title}, len={len(content)}")

settings = Settings()
try:
    facts = extract_with_thor(store.path, "test_run", doc_id, title, content, settings)
    print(f"Success! Extracted {len(facts)} facts from {doc_id}")
except Exception as e:
    print(f"Exception caught: {type(e).__name__}: {e}")
    traceback.print_exc()
