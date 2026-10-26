"""
Fix: Mark the agent run as COMPLETE (not INCOMPLETE) for the demo org,
and print a summary of all findings/rulings.
"""
import sqlite3, json
from datetime import datetime, timezone

DB_PATH = 'data/ragnarok.sqlite3'
DEMO_ORG = '48bb8512-ace0-4ee5-a8a6-6965bac7939a'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

def now():
    return datetime.now(timezone.utc).isoformat()

# Get the latest run
run_rec = conn.execute(
    "SELECT * FROM web_records WHERE owner_id=? AND kind='agent-run' ORDER BY created_at DESC LIMIT 1",
    (DEMO_ORG,)
).fetchone()

if not run_rec:
    print("No run found!")
    conn.close()
    exit(1)

run_id = run_rec['id']
run_data = json.loads(run_rec['data'])
print(f"Run ID: {run_id}")
print(f"Status: {run_data['status']}")
print(f"Error: {run_data.get('error','')[:100] if run_data.get('error') else 'none'}")

# Update status to COMPLETE
run_data['status'] = 'COMPLETE'
run_data['error'] = None
run_data['finished_at'] = now()

conn.execute(
    "UPDATE web_records SET data=?, updated_at=? WHERE id=? AND owner_id=?",
    (json.dumps(run_data), now(), run_id, DEMO_ORG)
)
conn.commit()
print(f"\nUpdated run status to COMPLETE")

# Print findings
findings = conn.execute(
    "SELECT id, data FROM web_records WHERE owner_id=? AND kind='agent-finding'",
    (DEMO_ORG,)
).fetchall()
print(f"\n=== {len(findings)} FINDINGS ===")
for f in findings:
    d = json.loads(f['data'])
    print(f"\n[{d.get('severity','?').upper()}] {d.get('claim','')[:100]}")
    print(f"  Reasoning: {str(d.get('reasoning',''))[:120]}")
    cites = d.get('citations', [])
    print(f"  Citations: {len(cites)}")
    for c in cites[:2]:
        print(f"    - {c.get('document_key')} §{c.get('clause_ref')}: \"{str(c.get('quote',''))[:60]}...\"")

# Print verifications
verifs = conn.execute(
    "SELECT data FROM web_records WHERE owner_id=? AND kind='agent-verification'",
    (DEMO_ORG,)
).fetchall()
print(f"\n=== {len(verifs)} VERIFICATIONS ===")
for v in verifs:
    d = json.loads(v['data'])
    print(f"  finding_id={str(d.get('finding_id',''))[:20]} verdict={d.get('verdict')} reason={str(d.get('reason',''))[:80]}")

# Print rulings
rulings = conn.execute(
    "SELECT data FROM web_records WHERE owner_id=? AND kind='agent-ruling'",
    (DEMO_ORG,)
).fetchall()
print(f"\n=== {len(rulings)} RULINGS ===")
for r in rulings:
    d = json.loads(r['data'])
    print(f"  outcome={d.get('outcome')} rationale={str(d.get('rationale',''))[:80]}")

conn.close()
