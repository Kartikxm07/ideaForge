# Ragnarok

Ragnarok is a privacy-first local agent runtime under development. The current release is a runnable API and worker with persistent tasks, exact approvals, a small allowlisted tool registry, local memory, source-text ingestion, exact quote checks, and bounded contract finding runs. It is **not yet a production SaaS**. The hosted control plane, web dashboard, encrypted memory, scheduler, and general-purpose sandbox are planned work.

The API binds to `127.0.0.1` and requires a bearer token. Private prompts and memory remain in the local SQLite database. The Ollama adapter accepts only a loopback HTTP origin and makes no cloud fallback.

## Quick start (Python 3.11+)

```powershell
python -m pip install -e '.[test]'
$env:RAGNAROK_API_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(48))"
python -m ragnarok.cli migrate
python -m ragnarok.cli doctor
python -m ragnarok.cli api
```

In another terminal with the same token and database settings:

```powershell
python -m ragnarok.cli worker
```

The API is at `http://127.0.0.1:8000/docs`. To use local model planning, run Ollama, pull the model named by `RAGNAROK_OLLAMA_MODEL` (default `llama3.2`), then call `POST /api/v1/tasks/from-prompt`. Explicit steps sent to `POST /api/v1/tasks` work without Ollama. The worker executes only built-in tools listed at `GET /api/v1/tools`.

To import the text contracts from an Odin developer pack you already have locally:

```powershell
python -m ragnarok.cli ingest-odin --bundle 'C:\path\to\odin_dev_pack\bundle'
```

This imports the contract `.txt` files and company context, preserving their source text and SHA-256 hashes. Search through `GET /api/v1/documents/search?q=...` and check a proposed quote and clause reference with `POST /api/v1/citations/verify`. A successful check means the exact quote appears under the named heading in the current document version; it does **not** decide whether a legal interpretation is correct.

Create a contract finding run with `POST /api/v1/analyses` using `question`, `focus`, `document_keys`, and `provider_kind`. The default `ollama` provider proposes hypotheses from bounded source excerpts; every citation must pass the exact-text gate before a finding is stored. `deterministic` is an offline comparison limited to uptime percentages in two commitment clauses. The worker processes the run, and `GET /api/v1/analyses/{id}` returns its state and evidence. Findings marked `EVIDENCE_CHECKED` have verified quote locations, **not verified legal conclusions**. Updating a source marks its runs stale; deleting a source removes runs derived from it.

## Test

```powershell
python -m pytest -q
python -m compileall -q ragnarok
```

See [architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [plan](docs/IMPLEMENTATION_PLAN.md), [data flow](docs/DATA_FLOW.md), and [threat model](docs/THREAT_MODEL.md).

