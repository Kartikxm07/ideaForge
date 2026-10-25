# INTEGRATION_PLAN: Architecture Blueprint & Implementation Strategy

**Project**: ODIN — Autonomous Contract Intelligence Engine  
**Challenge**: Quillhub Autonomous Contract Intelligence Challenge  
**Evaluation Date**: 2026-10-25  
**Target Repository Root**: `e:\ideaForge\ideaForge`

---

## 1. Executive Summary & Orchestration Strategy

ODIN will be implemented by extending the existing Python `ragnarok` runtime with a modular **LangGraph state-machine workflow** and wiring it into the existing **Next.js 16 / React 19 frontend**.

### Architectural Decisions
1. **Orchestrator**: **LangGraph (Python 3.11)**  
   - *Justification*: `langgraph` v1.1.3 is already installed in the environment. It provides native support for directed cyclical graphs, bounded loop iterations (circuit breakers), conditional edge routing, typed state serialization, and checkpointing.
2. **State Store**: **SQLite via extended `ragnarok` migrations**  
   - *Justification*: The repo already uses SQLite in `ragnarok/store.py` with an established migration runner. Rather than introducing a second database or loose JSON files, we will add migrations `006_odin_state.sql` to house all 16 Odin tables with strict typing and foreign keys.
3. **Backend Location**: Integrated directly within `ragnarok/`  
   - We will structure the new backend capabilities under `ragnarok/odin/`:
     - `ragnarok/odin/core/`: Models, config, store extensions, message bus.
     - `ragnarok/odin/engine/`: Ingest, citation verifier, calc (dates/SLA/business days), terms merge, event parser, budget guard, Claude client.
     - `ragnarok/odin/agents/`: Odin router, Thor, Heimdall-1, Norns, Loki, Heimdall-2, Tyr, Synthesis.
     - `ragnarok/odin/graph/`: LangGraph state machine definition.
   - The FastAPI instance in `ragnarok/api.py` will mount the `/api/v1/odin/*` routes.
4. **Frontend Integration**:  
   - Update `src/frontend/store/useOdinStore.ts` to fetch real data from `/api/v1/odin/*` while keeping fallbacks.
   - Restore the full multi-view War Room dashboard in `src/frontend/app/war-room/page.tsx`, rendering all 7 views (`ContractGraphView`, `ExposureView`, `TimelineView`, `DebateView`, `ActionsView`, `PlanView`, `TraceView`).

---

## 2. Target Folder Layout

```
ideaForge/
├── ragnarok/
│   ├── ... (existing modules)
│   ├── migrations/
│   │   ├── ... (001 to 005)
│   │   └── 006_odin_state.sql       # New Odin tables
│   └── odin/
│       ├── __init__.py
│       ├── config.py                # Model names, limits, timeouts, thresholds
│       ├── models.py                # Pydantic schemas matching state tables
│       ├── store_ext.py             # SQLite helper queries for Odin state
│       ├── bus.py                   # Typed message bus & event logger
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── ingest.py            # Stable clause ID chunking & indexing
│       │   ├── verifier.py          # Strict verbatim quote checker
│       │   ├── calc.py              # Date math, holiday calendars, SLA uptime & credits
│       │   ├── terms_merge.py       # Amendment overrides (A3/A2, B2/B1) & STD resolution
│       │   ├── event_parser.py      # Safe JSONL parser with quarantine
│       │   ├── budget_guard.py      # LLM token & call circuit breakers
│       │   └── llm_client.py        # Anthropic Claude wrapper with backoff, retry & cache
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── prompts/             # System prompts for all agents
│       │   │   ├── thor_system.txt
│       │   │   ├── heimdall1_system.txt
│       │   │   ├── loki_system.txt
│       │   │   ├── heimdall2_system.txt
│       │   │   ├── tyr_system.txt
│       │   │   └── synthesis_system.txt
│       │   ├── odin_router.py       # Orchestrator, planning, loop counters, gate
│       │   ├── thor.py              # Evidence-grounded contract extraction
│       │   ├── heimdall_1.py        # Operational event monitor & clause mapping
│       │   ├── norns.py             # Timeline, commitments, exposure math
│       │   ├── loki.py              # Adversarial reviewer (per-contract & cross-contract)
│       │   ├── heimdall_2.py        # Independent finding verifier (3 checks + calc)
│       │   ├── tyr.py               # Dispute arbiter & draft notice generator
│       │   └── synthesis.py         # Per-contract and company risk reports
│       └── graph/
│           ├── __init__.py
│           ├── state.py             # OdinGraphState definition
│           └── pipeline.py          # Compiled LangGraph workflow
├── src/frontend/
│   ├── ...
│   ├── lib/
│   │   └── api-client.ts            # Client for FastAPI /api/v1/odin/* endpoints
│   ├── store/
│   │   └── useOdinStore.ts          # Synchronized with live API & checkpoint changes
│   └── app/
│       └── war-room/page.tsx        # Active multi-tab intelligence dashboard
```

---

## 3. Database Schema Extensions (`006_odin_state.sql`)

The following tables will be added to the SQLite store:

1. `odin_workstreams`: Tracks `contract` and `cross` workstream statuses (`pending`, `running`, `done`, `incomplete`).
2. `odin_extractions`: Extracted terms with verbatim citations, confidence scores, and ambiguity flags.
3. `odin_effective_terms`: Merged terms reflecting amendments (e.g. A3 superseding A2) and standard term incorporations.
4. `odin_event_map`: Operational events linked to document clauses with relevance (`action`/`info`/`noise`) and validity flags.
5. `odin_alerts`: Time-sensitive alerts rated by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
6. `odin_timeline`: Events, deadlines, and milestones per checkpoint `t` and doc.
7. `odin_exposure`: Financial liability breakdowns (expected vs worst-case) with formulas.
8. `odin_findings`: Loki risk hypotheses, attack paths, severity, likelihood, and status (`proposed`, `confirmed`, `challenged`, `ruled`).
9. `odin_clarifications`: Targeted Q&A loop between Loki and Thor.
10. `odin_verifications`: Heimdall-2 verdicts on Loki findings with clause, event, and code checks.
11. `odin_rulings`: Tyr arbitration decisions (`upheld`, `rejected`, `partial`) with rationale.
12. `odin_actions`: Notice drafts (termination, cure, SLA rejection, etc.) with verified footnotes and human approval gates.
13. `odin_messages`: Transition envelope log between all agents.
14. `odin_llm_calls`: Audit log of tokens, prompts, latency, and cache hits.
15. `odin_snapshots`: Pre-computed JSON payload for instant UI rendering across checkpoints (`CP1`, `CP2`, `CP3`).
16. `odin_reports`: Markdown & structured company/contract synthesis reports.

---

## 4. API Endpoints to Add

Mounted on FastAPI in `ragnarok/api.py`:

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/odin/run` | POST | Trigger analysis run across all or specific checkpoints |
| `/api/v1/odin/status` | GET | Current progress, active agent, workstream status |
| `/api/v1/odin/snapshots/{checkpoint_id}`| GET | Complete dashboard payload for checkpoint (`CP1`, `CP2`, `CP3`) |
| `/api/v1/odin/graph` | GET | Contract dependency & conflict graph nodes/edges (FR9.1) |
| `/api/v1/odin/exposure` | GET | Financial exposure figures & risk heatmap matrix (FR9.3) |
| `/api/v1/odin/timeline` | GET | Timeline milestones & Gantt swimlanes as of clock `t` (FR9.2) |
| `/api/v1/odin/findings` | GET | Loki findings, Heimdall verifications, and Tyr rulings (FR9.4) |
| `/api/v1/odin/alerts` | GET | Prioritized alert feed (FR9.5) |
| `/api/v1/odin/actions` | GET | Drafted legal/operational notices with citations |
| `/api/v1/odin/actions/{id}/approve` | POST | Human sign-off approving a notice |
| `/api/v1/odin/actions/{id}/reject` | POST | Human rejection of a notice with reason |
| `/api/v1/odin/reports` | GET | Synthesis reports (Company Risk Report + Per-contract Reports) |
| `/api/v1/odin/telemetry` | GET | Agent message bus & LLM call telemetry log (NFR4) |

---

## 5. LangGraph Workflow Graph

```mermaid
flowchart TD
    START([START]) --> INGEST[Ingest & Clause Indexing]
    INGEST --> PLAN[Odin Planner]
    PLAN --> THOR[Thor Contract Extraction]
    THOR --> MERGE[Terms Merge & Amendment Override]
    MERGE --> CHECKPOINT_LOOP{For each Checkpoint t in [CP1, CP2, CP3]}
    
    CHECKPOINT_LOOP --> HEIMDALL_1[Heimdall-1 Event Monitor & Notice Validity]
    HEIMDALL_1 --> NORNS[Norns Timeline & Deterministic Calc]
    NORNS --> LOKI[Loki Adversarial Review & Cross-Contract Attack]
    LOKI --> CLARIFY_CHECK{Need Thor Clarification?}
    CLARIFY_CHECK -- Yes, round < MAX --> THOR_CLARIFY[Thor Targeted Clause Re-extract]
    THOR_CLARIFY --> LOKI
    CLARIFY_CHECK -- No --> HEIMDALL_2[Heimdall-2 Verification 3-Checks + Code]
    
    HEIMDALL_2 --> DEBATE_CHECK{Dispute on Finding?}
    DEBATE_CHECK -- Agreed / Confirmed --> TYR_ACTION[Tyr Action Drafter]
    DEBATE_CHECK -- Challenged, round < MAX --> LOKI_REBUT[Loki Rebuttal]
    LOKI_REBUT --> TYR_RULING[Tyr Adjudication]
    TYR_RULING --> TYR_ACTION
    
    TYR_ACTION --> SNAPSHOT[Save Checkpoint Snapshot]
    SNAPSHOT --> CHECKPOINT_LOOP
    
    CHECKPOINT_LOOP -- All Checkpoints Evaluated --> GATE[Odin Completeness Gate]
    GATE -- Pass --> SYNTHESIS[Synthesis Per-Contract & Company Reports]
    GATE -- Fail / Incomplete --> SYNTHESIS
    SYNTHESIS --> END([END])
```

---

## 6. Implementation Phases Roadmap

- **Phase 1: Repo Recon & Integration Plan (COMPLETE)**
  - Deliverables: `REPO_MAP.md`, `INTEGRATION_PLAN.md`.
  - Halt for user approval.
- **Phase 2: Foundations**
  - Schema migration `006_odin_state.sql`.
  - Deterministic engine modules (`ingest`, `verifier`, `calc`, `event_parser`, `budget_guard`, `llm_client`).
  - Unit test suite demonstrating citation validation, date calculations, and bad-event quarantine.
- **Phase 3: Odin Plan + Thor + Terms Merge**
  - Odin planner and status board.
  - Thor extraction prompts with Pydantic JSON schemas.
  - `terms_merge` applying A3 over A2 and B2 over B1.
  - Targeted clause re-extraction with cache.
- **Phase 4: Clock + Heimdall-1 + Norns**
  - Simulated clock runner across the 3 checkpoints.
  - Heimdall-1 event classification and notice legality evaluation.
  - Norns deterministic timeline and exposure engine.
  - Snapshot generator.
- **Phase 5: Loki + Heimdall-2 + Tyr + Odin Router**
  - Loki adversarial attack generator (per-contract and cross-contract).
  - Heimdall-2 3-check verifier + code check.
  - Tyr dispute ruling and action drafter.
  - Bounded debate and clarification loops.
- **Phase 6: Full Pipeline, Completeness Gate, Synthesis, API**
  - End-to-end orchestration workflow.
  - Completeness gate validation.
  - Company risk report and per-contract synthesis generation.
  - FastAPI endpoints for frontend communication.
- **Phase 7: Dashboard Integration, Acceptance, Polish**
  - Connect Next.js frontend to real backend endpoints.
  - Time slider interaction verification.
  - Complete execution of Acceptance Test suite (T1 through T16).
  - Final report deliverables: `ACCEPTANCE_REPORT.md` and `RUN_GUIDE.md`.

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **LLM Hallucinations / Fake Clauses** | Evaluator penalty for uncited or inaccurate claims | Strict deterministic `citation_verifier` validates every quote as an exact substring of canonical `.txt` files before writing to the database. |
| **Model Rate Limits or API Outages** | Pipeline failure mid-evaluation | Exponential backoff, timeout handling, JSON-schema repair retries, and local deterministic caching by prompt SHA-256 hash. |
| **Infinite Agent Debate Loops** | High token usage and evaluation timeouts | Hard caps: `MAX_CLARIFY_PER_FINDING=2`, `MAX_DEBATE_ROUNDS=2`, global budget circuit breaker. |
| **UI and Backend Desynchronization** | Broken dashboard during demo | Shared Pydantic / TypeScript schemas in `types/odin.ts` and automated API integration smoke tests. |
| **Silent Assumption of Missing Documents** | Inaccurate conclusions (e.g. B2 missing exhibits) | Ambiguity flags (`ambiguity_flag=True`) surfaced prominently with zero fabricated content. |
