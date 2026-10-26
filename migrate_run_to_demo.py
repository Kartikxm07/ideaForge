"""
Migrate the latest completed agent run from suman-org to demo-org
so the War Room (logged in as demo@ragnarok.local) shows all the data.
"""
import sqlite3, json, uuid
from datetime import datetime, timezone

DB_PATH = 'data/ragnarok.sqlite3'
SUMAN_ORG = '149b8919-d90c-4007-bf0f-1b8d33414ac6'
DEMO_ORG = '48bb8512-ace0-4ee5-a8a6-6965bac7939a'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

def now():
    return datetime.now(timezone.utc).isoformat()

# Get the latest agent run from suman org
runs = conn.execute(
    "SELECT * FROM web_records WHERE owner_id=? AND kind='agent-run' ORDER BY created_at DESC",
    (SUMAN_ORG,)
).fetchall()
print(f"Suman org runs: {len(runs)}")

if not runs:
    print("No runs found!")
    conn.close()
    exit(1)

# Pick the run with most activity
best_run = None
best_count = 0
for r in runs:
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM web_records WHERE owner_id=? AND data LIKE ?",
        (SUMAN_ORG, f'%"run_id": "{r["id"]}"%')
    ).fetchone()['cnt']
    d = json.loads(r['data'])
    print(f"  run {r['id'][:30]} status={d.get('status')} children={count}")
    if count > best_count:
        best_count = count
        best_run = r

print(f"\nMigrating best run: {best_run['id'][:30]} with {best_count} children")

# Get all child records for this run
children = conn.execute(
    "SELECT * FROM web_records WHERE owner_id=? AND (id=? OR data LIKE ?)",
    (SUMAN_ORG, best_run['id'], f'%"run_id": "{best_run["id"]}"%')
).fetchall()
print(f"Children: {len(children)}")

# Migrate all with new IDs, remapping run_id
old_run_id = best_run['id']
new_run_id = str(uuid.uuid4())
print(f"New run ID: {new_run_id}")

migrated = 0
for r in children:
    old_data = json.loads(r['data'])
    # Remap run_id
    if old_data.get('run_id') == old_run_id:
        old_data['run_id'] = new_run_id
    new_id = new_run_id if r['kind'] == 'agent-run' else str(uuid.uuid4())
    
    # Upsert into demo org
    existing = conn.execute("SELECT id FROM web_records WHERE id=?", (new_id,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE web_records SET data=?, updated_at=? WHERE id=?",
            (json.dumps(old_data), now(), new_id)
        )
    else:
        conn.execute(
            "INSERT INTO web_records(id, owner_id, kind, data, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (new_id, DEMO_ORG, r['kind'], json.dumps(old_data), r['created_at'], r['updated_at'])
        )
    migrated += 1

conn.commit()

# Verify
kinds = conn.execute(
    "SELECT kind, COUNT(*) as cnt FROM web_records WHERE owner_id=? GROUP BY kind ORDER BY kind",
    (DEMO_ORG,)
).fetchall()
print(f"\nDemo org web_records after migration:")
for k in kinds:
    print(f"  {k['kind']}: {k['cnt']}")

# Final check - what run looks like
run_data = conn.execute(
    "SELECT data FROM web_records WHERE owner_id=? AND kind='agent-run' ORDER BY created_at DESC LIMIT 1",
    (DEMO_ORG,)
).fetchone()
if run_data:
    d = json.loads(run_data['data'])
    print(f"\nLatest run: status={d.get('status')} docs={d.get('document_keys')}")

conn.close()
print(f"\nMigrated {migrated} records to demo org")
