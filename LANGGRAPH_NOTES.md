# ODIN LangGraph implementation notes

Checked in the local Python environment on 2026-10-25:

| Distribution | Installed version |
| --- | --- |
| `langgraph` | 1.0.10 |
| `langchain-core` | 1.2.18 |
| `langgraph-checkpoint` | 3.0.0 |
| `langgraph-checkpoint-sqlite` | 3.0.3 |
| `anthropic` | 0.72.0 |

Verified imports:

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, Command, interrupt
from langgraph.config import get_stream_writer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
```

`StateGraph.add_conditional_edges(source, path, path_map=None)` supports the deterministic routers. `StateGraph.compile(checkpointer=...)` accepts `SqliteSaver`. `SqliteSaver.from_conn_string(path)` is a context manager. A compiled subgraph can be added as a node. `get_graph(xray=True).draw_mermaid()` expands it; the generated result is in [`docs/graph.mmd`](docs/graph.mmd). An in-memory SQLite graph invocation and an application integration test both passed.

A live OpenRouter smoke run against `openai/gpt-oss-120b` also completed using a small synthetic agreement in a temporary database: 4 cited extractions, 2 dated timeline items, 4 findings, 4 verifications, and 4 rulings. This checks connectivity and the full current graph without adding test documents to the user's workspace.

## Current wiring

- The existing `/api/v1/workspace/agents/run` endpoint calls `execute_run`, which delegates to `ragnarok.agent_graph.execute_graph`.
- A separate SQLite checkpoint database lives next to the business database as `<db path>.langgraph.sqlite3`. The LangGraph `thread_id` is the run ID. Source text, citations, model responses, and results remain in the owner-scoped application database.
- Odin fans out Thor via `Send` for each document. A compiled debate subgraph routes Loki challenges to Heimdall, optionally through one Loki rebuttal, then to Tyr. A gate marks incomplete runs and preserves prior verified outputs.
- A successful model response is cached by run, node, and prompt hash before the graph advances. This prevents repeated calls on graph resume after a saved response. A crash between the remote call and the cache write can still repeat that call.
- `POST /api/v1/workspace/agents/runs/{run_id}/resume` resumes an interrupted `RUNNING` run. The existing dashboard polling response remains compatible.
- The configured provider is OpenRouter using `openai/gpt-oss-120b`; the key is read from local environment settings and is never placed in graph state or notes.

## Current limits

The graph is agentic orchestration over the **existing** ODIN data model. It does not yet implement normalized evidence/exposure tables, amendment precedence, holiday and ledger inputs, monetary exposure formulas, source-driven multiple clock checkpoints, or targeted Thor clarification. `terms_merge` retains all cited terms and labels amendment precedence unresolved; `norns_delta` computes no monetary exposure. The snapshot stores `exposure: null`. The current workflow has a single run-start checkpoint. Results must not be described as a financial forecast.

The graph uses up to 80 cached model responses per run, one rebuttal per challenged finding, and a recursion limit of 64. Reaching the graph recursion limit marks the run `INCOMPLETE`. Model response caching counts successful outputs, not failed API attempts. These limits need configuration and more adversarial coverage before scaling beyond the current 20-document upload cap.

Docker inspection on this machine found a separate `hyd-ps2` stack. Its backend image has no `ragnarok` package. ODIN's current API is the local `uvicorn ragnarok.api` process on `127.0.0.1:8000`, with local Next.js on `127.0.0.1:3001`. This checked graph therefore runs in that local ODIN Python process. The SQLite checkpointer is an embedded Python package; it does not require a SQLite server container.
