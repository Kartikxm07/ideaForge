"""
Directly run ODIN agents for the org by calling the Python API (bypassing HTTP auth).
This creates a new agent run and executes it synchronously.
"""
import sys
sys.path.insert(0, '.')

from ragnarok.config import Settings
from ragnarok.store import Store
from ragnarok.model import ClaudeProvider
from ragnarok.agents import start_run, execute_run, latest_view

settings = Settings.from_env()
store = Store(settings.db_path)
store.migrate()
model = ClaudeProvider(settings)

ORG_ID = "149b8919-d90c-4007-bf0f-1b8d33414ac6"

print(f"Settings: model_heavy={settings.model_heavy}")
print(f"Owner (org): {ORG_ID}")

# Get available documents for this org
with store.connect() as db:
    docs = db.execute(
        "SELECT document_key FROM documents WHERE owner_id=? ORDER BY document_key",
        (ORG_ID,)
    ).fetchall()

doc_keys = [d['document_key'] for d in docs if d['document_key'] != 'context']
print(f"\nDocuments available ({len(doc_keys)}): {doc_keys}")

# Check if there's already a running/complete run
current = latest_view(store, ORG_ID)
if current:
    print(f"\nExisting run: status={current['status']} id={current.get('id')}")
    print(f"  extractions={len(current.get('extractions',[]))} findings={len(current.get('findings',[]))} messages={len(current.get('messages',[]))}")

# Start a new run
print(f"\nStarting new agent run with {len(doc_keys)} contracts...")
run = start_run(store, ORG_ID, doc_keys[:9])  # max 9 contracts
print(f"Run started: id={run['id']} status={run['status']}")

# Execute the run
print("\nExecuting agent debate... (this may take several minutes)")
execute_run(store, ORG_ID, run['id'], model)

# Check results
result = latest_view(store, ORG_ID)
print(f"\n=== RESULTS ===")
print(f"Status: {result['status']}")
print(f"Extractions: {len(result.get('extractions',[]))}")
print(f"Findings: {len(result.get('findings',[]))}")
print(f"Verifications: {len(result.get('verifications',[]))}")
print(f"Rulings: {len(result.get('rulings',[]))}")
print(f"Messages: {len(result.get('messages',[]))}")
print(f"Timeline: {len(result.get('timeline',[]))}")
if result.get('error'):
    print(f"Error: {result['error']}")
