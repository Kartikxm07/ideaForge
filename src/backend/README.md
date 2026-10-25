# ODIN Backend — `src/backend`

This folder organises the ODIN Python backend source code within the monorepo.

> The live Python package lives at `ragnarok/` in the project root (installed as `ragnarok-local`).  
> This folder is the **human-readable, organized view** of those modules for development.

## Folder Layout

```
src/backend/
├── agents/          ← One file per ODIN specialist agent
│   ├── __init__.py
│   ├── thor.py      ← Extraction & citation
│   ├── heimdall.py  ← Evidence verification
│   ├── norns.py     ← Timeline & deadline simulation
│   ├── loki.py      ← Adversarial risk analysis
│   └── tyr.py       ← Adjudication & action drafting
├── api/             ← FastAPI routers (entry points)
│   ├── __init__.py
│   └── workspace.py ← Workspace routes (mirrors ragnarok/workspace_api.py)
├── core/            ← Shared utilities
│   ├── __init__.py
│   ├── config.py    ← Environment settings
│   ├── model.py     ← LLM provider (OpenRouter / Claude)
│   ├── store.py     ← SQLite store
│   └── rag.py       ← RAG pipeline
└── README.md
```

## Running the Backend

```powershell
# From repo root
python -m ragnarok.cli migrate
python -m ragnarok.cli api      # FastAPI on http://127.0.0.1:8000
python -m ragnarok.cli worker   # Background task worker
```

The API docs are available at `http://127.0.0.1:8000/docs`.
