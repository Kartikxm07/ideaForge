"""
Trigger a fresh full ODIN agent run for demo org via the internal API.
"""
import sys, json, time, requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "http://127.0.0.1:8000"

# Load API token from .env
import os
from pathlib import Path
dotenv = {}
for line in Path('.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        dotenv[k.strip()] = v.strip().strip('"\'')

API_TOKEN = os.getenv('RAGNAROK_API_TOKEN') or dotenv.get('RAGNAROK_API_TOKEN', '')
DEMO_USER_TOKEN = None

print(f"API Token (first 10): {API_TOKEN[:10]}...")

# Login as demo user
resp = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "demo@ragnarok.local",
    "password": "demo1234"
}, timeout=10)
print(f"Login: {resp.status_code}")
if resp.status_code == 200:
    DEMO_USER_TOKEN = resp.json().get('token')
    print(f"User token: {DEMO_USER_TOKEN[:20]}...")
else:
    print(f"Login failed: {resp.text[:200]}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {DEMO_USER_TOKEN}"}

# Get existing contracts
resp = requests.get(f"{BASE}/api/v1/workspace/contracts", headers=headers, timeout=10)
print(f"\nContracts: {resp.status_code}")
contracts = resp.json() if resp.status_code == 200 else []
print(f"Found {len(contracts)} contracts")
for c in contracts[:5]:
    print(f"  {c.get('document_key')}: {c.get('title')}")

# Start a new analysis run
resp = requests.post(f"{BASE}/api/v1/runs", headers=headers, json={}, timeout=30)
print(f"\nStart run: {resp.status_code}")
if resp.status_code in (200, 201):
    run = resp.json()
    run_id = run.get('id') or run.get('run_id')
    print(f"Run started! ID: {run_id}")
    print(f"Status: {run.get('status')}")
else:
    print(f"Start run failed: {resp.text[:300]}")
