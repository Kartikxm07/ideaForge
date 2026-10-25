# ODIN local demo

This demo reads the fictional Quillhub dataset from SQLite. It shows source contract clauses and events at the organizer's simulated checkpoints. Findings, exposure, alerts, actions, and execution traces appear only after a backend process has stored those records. The current branch does not generate the full multi-agent output automatically.

## Start on Windows PowerShell

Use Python 3.11+ and Node.js 20+. Run these commands from the repository root. Choose a private token of at least 32 characters and use the same value in both terminals. Do not commit it.

```powershell
python -m pip install -e ".[test]"
$env:RAGNAROK_API_TOKEN = "replace-with-your-own-private-random-value-at-least-32-chars"
$env:RAGNAROK_OWNER_ID = "demo-owner"
$env:RAGNAROK_DB_PATH = "data/odin-demo.sqlite3"
python -m ragnarok.cli ingest-odin --bundle odin_dev_pack/bundle
python -m ragnarok.cli ingest-events --file odin_dev_pack/bundle/events/events_drop1.jsonl
python -m ragnarok.cli ingest-events --file odin_dev_pack/bundle/events/events_drop2.jsonl
python -m ragnarok.cli api
```

In a second PowerShell terminal:

```powershell
cd src/frontend
npm ci
$env:RAGNAROK_API_TOKEN = "the-same-private-value-used-above"
$env:RAGNAROK_API_URL = "http://127.0.0.1:8000"
npx next dev -H 127.0.0.1
```

Open `http://127.0.0.1:3000/war-room`. The Next.js server passes the token to the loopback Python API; the token is not sent to browser JavaScript. Both servers should stay bound to loopback. For a production build, run `npm run build` and `npx next start -H 127.0.0.1` in the frontend directory. Set `BETTER_AUTH_SECRET` to a private value for the unused legacy auth route if it is enabled.

## Evaluator walkthrough

1. Select contract **B2** to see the incomplete-document warning and source clauses. Select any clause to read its exact source text.
2. Switch from **2027-03-15** to **2027-06-01**. The event count and event list change according to stored event timestamps. Expand an event to read its original body.
3. Open **Financial exposure**, **Findings**, and **Alerts & actions**. If the engine has not stored output for the checkpoint, each panel says so instead of showing guessed numbers or decisions.
4. Open **Execution & data quality** to see analysis/task status and the quarantined malformed line from the second event drop.
5. Use **Refresh data** after any backend ingest or analysis operation.

## Current boundaries

- The graph has document-to-clause edges from persisted extraction; cross-contract dependency and conflict edges have not been verified.
- The checkpoint control filters persisted events and selects any stored checkpoint output. It does not run an obligation recomputation.
- Exposure, verified agent debate, alert creation, notice drafting, ODIN approval, and outbound sending require backend workflows that are not implemented on this branch. The UI never presents these as complete.
- The organizer PDF and dataset format specification are present under `odin_dev_pack/`. `ODIN_MASTER_PROMPT.md` was not present in this checkout during implementation.
