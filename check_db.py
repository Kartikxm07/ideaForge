import sqlite3, json

DB_PATH = 'data/ragnarok.sqlite3'
ORG_ID = '149b8919-d90c-4007-bf0f-1b8d33414ac6'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Check agent-run
runs = conn.execute("SELECT id, data FROM web_records WHERE owner_id=? AND kind='agent-run'", (ORG_ID,)).fetchall()
print(f"Agent runs for org: {len(runs)}")
for r in runs:
    d = json.loads(r['data'])
    print(f"  run_id={r['id']} status={d.get('status')} keys={d.get('document_keys')} started={d.get('started_at')}")

# Check data kinds under org
kinds = conn.execute("SELECT kind, COUNT(*) as cnt FROM web_records WHERE owner_id=? GROUP BY kind", (ORG_ID,)).fetchall()
print(f"\nweb_records by kind under org:")
for k in kinds:
    print(f"  {k['kind']}: {k['cnt']}")

# Check agent extractions  
ext = conn.execute("SELECT data FROM web_records WHERE owner_id=? AND kind='agent-extraction'", (ORG_ID,)).fetchall()
print(f"\nExtractions: {len(ext)}")
if ext:
    print(json.loads(ext[0]['data']))

# Check agent messages (first 3)
msgs = conn.execute("SELECT data FROM web_records WHERE owner_id=? AND kind='agent-message' LIMIT 3", (ORG_ID,)).fetchall()
print(f"\nMessages (first 3):")
for m in msgs:
    d = json.loads(m['data'])
    print(f"  {d.get('from')} -> {d.get('to')}: {str(d.get('message',''))[:80]}")

conn.close()
