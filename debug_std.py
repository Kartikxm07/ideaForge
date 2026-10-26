"""
Debug: find the exact ProgrammingError for STD doc.
"""
import sys, json, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = 'data/ragnarok.sqlite3'
OWNER = '48bb8512-ace0-4ee5-a8a6-6965bac7939a'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# 1. Check STD doc exists in org
rows = conn.execute("SELECT owner_id, document_key, length(content) as clen FROM documents WHERE document_key='STD'").fetchall()
print(f"STD doc exists in {len(rows)} owner(s):")
for r in rows:
    print(f"  owner={r['owner_id']} length={r['clen']}")

# 2. Check rag_chunks for STD
chunks = conn.execute("SELECT owner_id, document_key, count(*) as cnt FROM rag_chunks WHERE document_key='STD' GROUP BY owner_id").fetchall()
print(f"\nRAG chunks for STD:")
for c in chunks:
    print(f"  owner={c['owner_id']} chunks={c['cnt']}")

# Check if rag_chunks has records for demo org
demo_chunks = conn.execute("SELECT count(*) as cnt FROM rag_chunks WHERE owner_id=?", (OWNER,)).fetchone()
print(f"\nTotal RAG chunks for demo org: {demo_chunks['cnt']}")

# 3. Check Thor/STD messages
fails = conn.execute("SELECT data FROM web_records WHERE kind='agent-message' AND data LIKE '%Thor/STD%' ORDER BY created_at DESC LIMIT 5").fetchall()
print(f"\nThor/STD messages:")
for f in fails:
    d = json.loads(f['data'])
    print(f"  {d.get('message','')[:300]}")

# 4. Check the schema of web_records
schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='web_records'").fetchone()
print(f"\nweb_records schema:\n{schema['sql']}")

# 5. Show all kinds in web_records for the latest run
run_id = '1d93e13a-2ad2-4a3b-80f3-80021883c149'
kinds = conn.execute("SELECT DISTINCT kind FROM web_records WHERE owner_id=? AND data LIKE ?", (OWNER, f'%{run_id}%')).fetchall()
print(f"\nKinds in run {run_id[:8]}...:")
for k in kinds:
    print(f"  {k['kind']}")

# 6. Count extractions for this run
exts = conn.execute("SELECT count(*) as cnt FROM web_records WHERE owner_id=? AND kind='agent-extraction'", (OWNER,)).fetchone()
print(f"\nTotal agent-extractions in demo org: {exts['cnt']}")

# 7. Show the STD extraction data sample
ext_sample = conn.execute("SELECT data FROM web_records WHERE owner_id=? AND kind='agent-extraction' LIMIT 1", (OWNER,)).fetchone()
if ext_sample:
    d = json.loads(ext_sample['data'])
    print(f"\nSample extraction document_key: {d.get('document_key','?')}")

# 8. Check if STD has extractions
all_exts = conn.execute("SELECT data FROM web_records WHERE owner_id=? AND kind='agent-extraction'", (OWNER,)).fetchall()
doc_keys = set()
for e in all_exts:
    d = json.loads(e['data'])
    doc_keys.add(d.get('document_key','?'))
print(f"\nDocuments with extractions: {sorted(doc_keys)}")

conn.close()
