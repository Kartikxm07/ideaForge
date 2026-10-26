"""
Re-ingest all docs for demo org with full chunking from TXT files.
Then trigger a fresh agent run.
"""
import sys, json, sqlite3, uuid, hashlib
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = 'data/ragnarok.sqlite3'
DEMO_ORG = '48bb8512-ace0-4ee5-a8a6-6965bac7939a'
PACK_DIR = Path('dataset/Pack/odin_dev_pack/bundle/contracts')
ODIN_PS_PATH = Path('dataset/Odin_PS.pdf')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

def now():
    return datetime.now(timezone.utc).isoformat()

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# Ingest TXT files for each contract
txt_files = sorted(PACK_DIR.glob('*.txt'))
print(f"Found {len(txt_files)} TXT files in {PACK_DIR}")

# For each txt, upsert the document and run chunking
for txt_path in txt_files:
    doc_key = txt_path.stem  # e.g. "A1", "STD"
    content = txt_path.read_text(encoding='utf-8', errors='replace')
    
    # Upsert document with full content
    sha = sha256(content)
    existing = conn.execute("SELECT id, content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (DEMO_ORG, doc_key)).fetchone()
    if existing:
        if existing['content_sha256'] != sha:
            conn.execute("UPDATE documents SET content=?, content_sha256=?, updated_at=? WHERE owner_id=? AND document_key=?",
                        (content, sha, now(), DEMO_ORG, doc_key))
            print(f"  Updated doc {doc_key} (content changed, len={len(content)})")
        else:
            print(f"  Doc {doc_key} unchanged (len={len(content)})")
    else:
        conn.execute("INSERT INTO documents(id, owner_id, document_key, title, content, content_sha256, source, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), DEMO_ORG, doc_key, f"{doc_key}.txt", content, sha, 'txt_ingest', now(), now()))
        print(f"  Inserted doc {doc_key} (len={len(content)})")
    conn.commit()

# Now run upsert_chunks for each doc
print(f"\nChunking all docs for demo org...")
from ragnarok.store import Store
from ragnarok.rag import upsert_chunks

store = Store(DB_PATH)
total_chunks = 0
for txt_path in txt_files:
    doc_key = txt_path.stem
    content = txt_path.read_text(encoding='utf-8', errors='replace')
    n = upsert_chunks(store, DEMO_ORG, doc_key, content)
    print(f"  {doc_key}: {n} chunks")
    total_chunks += n

print(f"\nTotal chunks: {total_chunks}")
final = conn.execute("SELECT count(*) as cnt FROM rag_chunks WHERE owner_id=?", (DEMO_ORG,)).fetchone()['cnt']
print(f"rag_chunks in demo org: {final}")

conn.close()
print("Done! Re-ingestion complete.")
