"""
Fix migration: web_records uses `id TEXT PRIMARY KEY` so the same ID cannot exist 
twice even with different owner_id. We need to generate new UUIDs for the copies.
"""
import sqlite3, json, uuid
from datetime import datetime, timezone

DB_PATH = 'data/ragnarok.sqlite3'
LOCAL_OWNER = 'local-owner'
ORG_ID = '149b8919-d90c-4007-bf0f-1b8d33414ac6'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Map old run_id -> new run_id so child records can reference the new run
id_map = {}

records = conn.execute(
    "SELECT * FROM web_records WHERE owner_id=? ORDER BY created_at", (LOCAL_OWNER,)
).fetchall()
print(f"Migrating {len(records)} web_records with new UUIDs...")

for r in records:
    old_id = r['id']
    old_data = json.loads(r['data'])
    
    # Generate a stable new ID based on ORG_ID + old_id hash
    new_id = str(uuid.uuid5(uuid.UUID(ORG_ID.replace('-', '').ljust(32, '0')[:32]), old_id))
    id_map[old_id] = new_id
    
    # Check if this new_id already exists under the org
    existing = conn.execute("SELECT id FROM web_records WHERE id=?", (new_id,)).fetchone()
    if existing:
        print(f"  = skip {r['kind']} (already migrated)")
        continue
    
    # Patch run_id references inside data
    if 'run_id' in old_data:
        old_run_id = old_data['run_id']
        new_run_id = str(uuid.uuid5(uuid.UUID(ORG_ID.replace('-', '').ljust(32, '0')[:32]), old_run_id))
        old_data['run_id'] = new_run_id
    
    try:
        conn.execute(
            "INSERT INTO web_records(id, owner_id, kind, data, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (new_id, ORG_ID, r['kind'], json.dumps(old_data), r['created_at'], r['updated_at'])
        )
        print(f"  + {r['kind']} old={old_id[:20]}... new={new_id[:20]}...")
    except Exception as ex:
        print(f"  ERR {r['kind']} {old_id[:20]}: {ex}")

conn.commit()

# Verify
kinds = conn.execute(
    "SELECT kind, COUNT(*) as cnt FROM web_records WHERE owner_id=? GROUP BY kind", (ORG_ID,)
).fetchall()
print(f"\nweb_records under org after migration:")
for k in kinds:
    print(f"  {k['kind']}: {k['cnt']}")

# Check run count
runs = conn.execute(
    "SELECT id, data FROM web_records WHERE owner_id=? AND kind='agent-run'", (ORG_ID,)
).fetchall()
print(f"\nAgent runs: {len(runs)}")
for r in runs:
    d = json.loads(r['data'])
    print(f"  {r['id'][:30]} status={d.get('status')} docs={d.get('document_keys')}")

conn.close()
print("\nMigration complete!")
