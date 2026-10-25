# Data flow and retention

| Boundary | Data | Trigger | Destination | Current policy |
| --- | --- | --- | --- | --- |
| Client → API | Token, prompt, steps, memory | User request | Loopback FastAPI | Required bearer token; no public bind in CLI |
| API → SQLite | Tasks, steps, outputs, memories, audit metadata | Request and execution | `RAGNAROK_DB_PATH` | Local persistent file; no automatic expiry yet |
| API → Ollama | Prompt and constrained planning instruction | Only `POST /api/v1/tasks/from-prompt` | Configured loopback origin | No cloud fallback; user controls Ollama installation |
| Worker → SQLite | Step status, output, events | Local polling | Same database | Transactional results; no external queue |
| Odin bundle → local runtime | Contract `.txt` files and company context | Explicit `ingest-odin` command | SQLite documents table | Paths constrained to bundle; 2 MB per document; no remote transfer |
| Local runtime → SaaS | None | Never in current implementation | None | SaaS control plane not implemented |

The local database is not encrypted by this application. The operator must protect the host account and storage. Task prompts, tool results, and imported source text are intentionally retained for inspection. Memory and document deletion remove their primary rows; there is no derived index or cache in this release. SQLite WAL files may persist until checkpointing, and backups remain the operator's responsibility. Do not place the database in a shared folder without understanding its access controls.

