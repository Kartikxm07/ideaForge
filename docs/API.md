# Current local API

All `/api/v1` routes require `Authorization: Bearer <RAGNAROK_API_TOKEN>`. The CLI binds to `127.0.0.1:8000`. OpenAPI is available at `/docs`. `GET /health/live` is public; `GET /health/ready` requires the token.

| Route | Purpose |
| --- | --- |
| `GET /api/v1/models/health` | Local Ollama/model availability |
| `GET /api/v1/tools` | Current allowlisted tool metadata |
| `POST /api/v1/tasks` | Create a bounded task from explicit steps; accepts `Idempotency-Key` |
| `POST /api/v1/tasks/from-prompt` | Ask local Ollama for a validated plan, then create task |
| `GET /api/v1/tasks`, `GET /api/v1/tasks/{id}` | Inspect owned tasks |
| `GET /api/v1/tasks/{id}/events?after=0` | Poll ordered event IDs for progress |
| `POST /api/v1/tasks/{id}/approve` | Approve a specific step with its returned digest |
| `POST /api/v1/tasks/{id}/cancel` | Cancel queued tasks |
| `GET/POST /api/v1/memories`, `PUT/DELETE /api/v1/memories/{id}` | Manage local memory |
| `GET /api/v1/memories/export` | Export owned memory as JSON |
| `GET/POST /api/v1/documents`, `GET/DELETE /api/v1/documents/{key}` | Manage source text |
| `GET /api/v1/documents/search?q=...` | Find an exact source snippet with a nearby heading |
| `POST /api/v1/citations/verify` | Verify exact quote and clause heading in current source text |
| `POST /api/v1/analyses` | Queue an Ollama or deterministic finding run; accepts `Idempotency-Key` |
| `GET /api/v1/analyses`, `GET /api/v1/analyses/{id}` | Inspect owned runs and evidence-checked findings |
| `POST /api/v1/analyses/{id}/cancel` | Cancel a queued finding run |
| `GET /api/v1/audit` | Inspect action metadata without raw prompt logging |

The API does not stream SSE yet. Clients can poll task events using the last seen event ID and analysis runs by ID. Model and document parsing errors are returned without internal tracebacks. Authentication is a single local token, not a cloud account system. Analysis findings are evidence-checked hypotheses, not validated legal opinions.

Example local analysis request after importing the Odin pack:

```json
{"question":"Compare upstream and downstream uptime commitments","focus":"Uptime","document_keys":["A2","B1"],"provider_kind":"deterministic"}
```

