# REPO_MAP: System Reconnaissance & Architecture Ground Truth

**Project**: ODIN — Autonomous Contract Intelligence Engine  
**Challenge**: Quillhub Autonomous Contract Intelligence Challenge (*Trial of the Nine Realms*)  
**Evaluation Date**: 2026-10-25  
**Canonical Repository Root**: `e:\ideaForge\ideaForge`

---

## 1. Repository Tree & Tech Stack

```
ideaForge/
├── .agents/                        # Agent workflows and skill configurations
├── .env.example                    # Environment variable template
├── docs/                           # Architecture, API, and ADR specifications
│   ├── ADR/
│   │   ├── 0001-local-runtime.md
│   │   ├── 0002-bounded-tools.md
│   │   └── 0003-evidence-gate.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DATA_FLOW.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── TESTING.md
│   └── THREAT_MODEL.md
├── odin_dev_pack/                  # Canonical Organizer Dataset & Specs
│   ├── README.md
│   ├── clock.json
│   ├── docs/
│   │   └── format_spec.md
│   └── bundle/
│       ├── manifest.json
│       ├── company/
│       │   └── context.txt
│       ├── contracts/
│       │   ├── STD.txt & STD.pdf   (Master Standard Terms)
│       │   ├── A1.txt & A1.pdf     (StratoNode Hosting Agreement)
│       │   ├── A2.txt & A2.pdf     (StratoNode SLA)
│       │   ├── A3.txt & A3.pdf     (StratoNode SLA Amendment No. 1)
│       │   ├── B1.txt & B1.pdf     (Harbor Retail Customer Agreement)
│       │   ├── B2.txt & B2.pdf     (Harbor DPA - incomplete exhibits)
│       │   ├── C1.txt & C1.pdf     (Vantage Logistics Agreement)
│       │   └── D1.txt & D1.pdf     (Pixelwright Contractor SOW)
│       ├── data/
│       │   ├── holidays.csv        (Observed business holidays)
│       │   └── payments_ledger.csv (Financial receivables & payables)
│       └── events/
│           ├── events_drop1.jsonl  (Events E-01 through E-10)
│           └── events_drop2.jsonl  (Events E-11 through E-18 + malformed line)
├── pyproject.toml                  # Python package configuration (ragnarok-local)
├── ragnarok/                       # Python Backend & Runtime Engine
│   ├── __init__.py
│   ├── analysis.py                 # Contract finding runs & citation gate
│   ├── api.py                      # FastAPI application routes
│   ├── cli.py                      # CLI entrypoint (ingest, migrate, worker, api)
│   ├── config.py                   # Settings loader
│   ├── documents.py                # Document ingestion, search, & citation verification
│   ├── model.py                    # Model provider abstraction
│   ├── operational_events.py       # Operational event stream ingest & quarantine
│   ├── store.py                    # SQLite store & migration manager
│   ├── tools.py                    # Tool registry
│   ├── workflow.py                 # Task execution state machine
│   └── migrations/
│       ├── 001_init.sql
│       ├── 002_documents.sql
│       ├── 003_analysis.sql
│       ├── 004_operational_events.sql
│       └── 005_event_import_errors.sql
├── src/frontend/                   # Next.js / React 19 Frontend Dashboard
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                (Root redirect to /login)
│   │   ├── login/page.tsx
│   │   ├── onboarding/page.tsx
│   │   ├── war-room/page.tsx       (Core Intelligence Dashboard)
│   │   ├── analysis/page.tsx       (Live Agent Council Telemetry)
│   │   ├── reports/page.tsx        (Portfolio & Contract Reports)
│   │   └── new-case/page.tsx
│   ├── components/
│   │   ├── hud/                    (HUD Header, KpiStrip, TimeSlider, Drawers, Modals)
│   │   ├── ui/                     (Complete shadcn / Radix component library)
│   │   └── views/
│   │       ├── ActionsView.tsx     (Draft notices & approve/reject panel)
│   │       ├── ContractGraphView.tsx (Interactive Contract Dependency Graph)
│   │       ├── DebateView.tsx      (Loki vs Heimdall vs Tyr council debate)
│   │       ├── ExposureView.tsx    (Financial risk heatmap & exposure breakdown)
│   │       ├── PlanView.tsx        (Odin workstreams & status tracking)
│   │       ├── TimelineView.tsx    (Simulated checkpoint timeline & Gantt swimlanes)
│   │       └── TraceView.tsx       (Agent message bus & telemetry log)
│   ├── mock/
│   │   └── odinData.ts             (Pre-populated mock data schema)
│   ├── store/
│   │   └── useOdinStore.ts         (Zustand reactive state management)
│   └── types/
│       └── odin.ts                 (Strict TypeScript interfaces for UI/Backend)
├── tests/
│   └── test_local_runtime.py       # Pytest suite for backend runtime (13 tests passing)
├── RAGNAROK_RUNTIME.md             # Runtime documentation
└── README.md                       # Architectural overview & challenge targets
```

### Stack Summary
- **Backend**: Python 3.11.0, FastAPI 0.162.0, Uvicorn 0.30+, Pydantic v2.11.7, LangGraph 1.1.3, Anthropic SDK 2.3.0, SQLite3, Pytest 9.1.1.
- **Frontend**: Next.js 16.1.1 (App Router), React 19.2.3, TypeScript 5, Tailwind CSS v4, Zustand 5.0, Radix UI / shadcn, Framer Motion 14, Recharts 2.15.

---

## 2. Organizer Specifications & Ground Rules

From `odin_dev_pack/docs/format_spec.md`:
1. **Canonical Citation Anchor**:
   > *"Each agreement is provided as a plain UTF-8 text file (`.txt`) with an identical twin document (`.pdf`). The `.txt` file is the canonical anchor for all citations and exact quote matching."*
2. **Citation Triple Rule**:
   Every surfaced finding, claim, or obligation must contain:
   - `Document ID`: Filename without extension (e.g. `"A1"`, `"B1"`, `"STD"`).
   - `Clause Reference`: Section number or heading as written in the contract (e.g. `"§3.1"`, `"Section 4.3"`).
   - `Verbatim Quote`: Exact substring from the `.txt` file supporting the finding.
3. **Two-Drop Event Model**:
   - **Drop 1 (`events_drop1.jsonl`)**: Initial portfolio analysis covering events `E-01` through `E-10`.
   - **Drop 2 (`events_drop2.jsonl`)**: Mid-cycle updates covering events `E-11` through `E-18`, with at least one intentionally malformed JSON line requiring safe quarantine.
4. **Grounded Reasoning**:
   - Explanation must detail *Who did what*, *Why it matters*, and *Legal / Financial Consequence*.

---

## 3. Data Inventory & Real Formats

| File | Type | Lines / Records | Canonical Details & Real Formats |
|---|---|---|---|
| `clock.json` | JSON | 9 lines | `start_date`: `"2027-01-15"`, `checkpoints`: `["2027-03-15", "2027-06-01", "2027-09-15"]` |
| `company/context.txt` | Text | 97 lines | Quillhub Inc. (Delaware; 1200 Innovation Dr, Austin TX). CEO: Priya Chandrasekaran; VP Legal: Marcus Ellison. Notice address: `legal-notices@quillhub.io`, Ops: `ops@quillhub.io`. Insurance: Meridian Mutual (CGL + Cyber/E&O) expiring **June 30, 2027**. |
| `contracts/STD.txt` | Text | 450 lines | Common Paper Cloud Service Agreement v2.0 Standard Terms. Incorporates Section 8 limitation of liability, Section 10 confidentiality, Section 12 notices. |
| `contracts/A1.txt` | Text | 108 lines | StratoNode Cover Page (2026-08-01). $8,000/mo hosting fee. Non-renewal notice: 30 days. Payment period: 30 days. |
| `contracts/A2.txt` | Text | 88 lines | StratoNode SLA. Uptime target: 99.5%. Credit tiers: <99.5% -> 10%, <99.0% -> 30%. Claim window: 30 days. Non-renewal: 30 days. |
| `contracts/A3.txt` | Text | 77 lines | SLA Amendment No. 1. **Overrides A2**: Claim window shortened to **15 days** (§2.1); non-renewal window increased to **60 days** (§2.2). |
| `contracts/B1.txt` | Text | 158 lines | Harbor Retail Agreement (2026-09-15). $40,000/mo. Uptime target: 99.9%. Claim window: 45 days. Termination for SLA miss: Section 8.1 requires **two consecutive calendar months**. Exclusivity: Section 6.1 (Enterprise tier for retail grocery in WA & OR). |
| `contracts/B2.txt` | Text | 188 lines | Harbor DPA. Line 183 explicitly states: `[NOTE: The remainder of this document, including Exhibit A... and Exhibit B... was not included in this copy. The document appears to be incomplete.]` |
| `contracts/C1.txt` | Text | 129 lines | Vantage Logistics Agreement. Execution 2026-11-10. Effective date triggers upon **Go-Live Date confirmation** (E-14: May 15, 2027). Setup fee: $12,000. Monthly fee: $18,500. Exclusivity: Section 4.1 (All tiers for 3PL warehousing/delivery in WA & OR). |
| `contracts/D1.txt` | Text | 239 lines | Pixelwright Design Studio SOW (2026-10-01). Milestones M1 ($10k), M2 ($15k), M3 ($20k), M4 ($12k). Section 4.2: 10 business days review window. Section 4.3: Failure to deliver written rejection deemed acceptance. Section 10.4: Amendments must be in writing and signed. |
| `data/payments_ledger.csv` | CSV | 26 transactions | Records hosting fees, customer payments, milestone disbursements. Row 21: `2027-04-08,Harbor Retail Group LLC,Quillhub Inc.,40000.00,April 2027 platform fee - QH-HARBOR-2026-001,overdue`. Discrepancy: Due date under B1 is 45 days from invoice (May 17, 2027). |
| `data/holidays.csv` | CSV | 12 lines (10 holidays) | Official business holidays across 2026–2027 (Thanksgiving, Christmas, New Year's, MLK Day, Presidents' Day, Memorial Day, Independence Day). Used for business day calculations. |
| `events/events_drop1.jsonl` | JSONL | 10 events | E-01 through E-10. Includes March 3 outage (E-04: 190 min), Vantage informal note (E-08), April invoice (E-09), Pixelwright oral delay call (E-10). |
| `events/events_drop2.jsonl` | JSONL | 9 lines | E-11 through E-18. E-11 (M4 delivery April 20), E-12 (May 1-2 outage, 505 min), E-14 (Vantage Go-Live May 15), E-16 (Insurance expiry warning), E-17 (Harbor credit claim). **Line 8 is intentionally malformed raw text**. |

---

## 4. Existing UI Capabilities & Gaps (FR9 Matrix)

| FR Item | Description | Existing UI Component | Status | Gap to Close |
|---|---|---|---|---|
| **FR9.1** | Interactive Contract Graph (nodes: docs/clauses; edges: dependency/conflict) | `components/views/ContractGraphView.tsx` | Component built with Framer Motion, filters, and node inspector | Wire from mock data (`mock/odinData.ts`) to backend API `/api/v1/graph` |
| **FR9.2** | Time Slider over clock checkpoints with live updating state | `components/hud/TimeSlider.tsx` | Slider UI with play/pause, step controls, and CP1/CP2/CP3 jumps | Connect `activeCheckpoint` changes to fetch `/api/v1/snapshots/{t}` |
| **FR9.3** | Financial Exposure Gauge + Risk Heatmap | `components/views/ExposureView.tsx` | Recharts bar charts, gross/net gauge, contract x month matrix | Connect to backend `/api/v1/exposure?checkpoint={t}` |
| **FR9.4** | Agent Debate Panel (Loki vs Heimdall vs Tyr with citations) | `components/views/DebateView.tsx` | Council debate cards with Loki attack path, Heimdall check, Tyr ruling | Wire to `/api/v1/findings?checkpoint={t}` & `/api/v1/rulings` |
| **FR9.5** | Alert Feed + Action Panel (Draft notices, clause citations, approve/reject) | `components/hud/AlertFeedRightRail.tsx` & `components/views/ActionsView.tsx` | Complete notice review UI with footnotes, authorized signatory checks, Approve/Reject buttons | Wire actions to `/api/v1/actions` and `/api/v1/actions/{id}/approve` |
| **NFR4** | Observability View (Work plan, status, transitions, completeness gate) | `components/views/PlanView.tsx` & `components/views/TraceView.tsx` | Multi-agent execution workflow rings, transition logs, workstreams | Wire to `/api/v1/workstreams`, `/api/v1/messages`, and `/api/v1/reports` |

---

## 5. Existing Backend / API Analysis

The `ragnarok` Python backend provides an excellent foundational runtime:
1. **SQLite Database & Migrations**:
   - `001_init.sql`: `tasks`, `steps`, `events`, `memories`, `audit_events`.
   - `002_documents.sql`: `documents` with SHA-256 content hashes and text indexing.
   - `003_analysis.sql`: `analysis_runs`, `analysis_hypotheses`, `analysis_findings`.
   - `004_operational_events.sql`: `operational_events` with `as_of` date filtering.
   - `005_event_import_errors.sql`: `event_import_errors` for quarantined malformed lines.
2. **Deterministic Citation Verification**:
   - `verify_citation(db, actor, document_key, clause_ref, quote)`: Verifies exact substring match under document sections.
3. **Document & Event Ingestors**:
   - `import_odin_bundle`: Ingests all text contracts, manifest, and company context into SQLite.
   - `import_event_drop`: Ingests JSONL events, atomically quarantine malformed lines.
4. **Current Limitations to Extend for Odin**:
   - Lacks the 6-agent Norse architecture (Thor, Norns, Loki, Heimdall, Tyr, Odin router).
   - Lacks `extractions`, `effective_terms`, `timeline`, `exposure`, `rulings`, `actions`, `messages`, and `snapshots` tables.
   - Lacks Claude API client with retry, budget guards, and schema validation.

---

## 6. Environment Verification

- **Python**: 3.11.0 (verified)
- **Node**: v24.18.0 (verified)
- **Dependencies Present**:
  - `anthropic` (2.3.0)
  - `langgraph` (1.1.3)
  - `fastapi` (0.162.0)
  - `pydantic` (2.11.7)
  - `pytest` (9.1.1)
- **Tests**: 13 of 13 tests passing in `tests/test_local_runtime.py`.
- **API Key**: `ANTHROPIC_API_KEY` environment variable configured.

---

## 7. Discrepancies: Master Prompt vs Repo Reality

| Item | Master Prompt Expectation | Repo Reality | Resolution |
|---|---|---|---|
| **Clock Checkpoints** | Table mentions 4 checkpoints: 2027-01-15, 2027-03-15, 2027-06-01, 2027-09-15 | `clock.json` has `start_date: "2027-01-15"` and `checkpoints: ["2027-03-15", "2027-06-01", "2027-09-15"]` (3 checkpoints) | Ground truth is `clock.json`: 2027-01-15 is start, followed by the 3 checkpoints. |
| **Model Names** | Mentions `claude-sonnet-5-5` & `claude-haiku-5-5` | Current valid Anthropic API models are `claude-3-7-sonnet-20250219` or `claude-3-5-sonnet-20241022` / `claude-3-5-haiku-20241022` | Configurable in `.env` / `config.py` defaulting to valid Claude 3.5/3.7 models with fallback. |
| **State Store** | Prompt suggests SQLite or JSON files | Existing SQLite store in `ragnarok/store.py` with migrations | Extend SQLite migrations in `ragnarok/migrations/` to keep single persistent store. |
| **Backend Framework** | Suggests Python + FastAPI + LangGraph | Repo already has `FastAPI` app in `ragnarok/api.py` and LangGraph installed | Integrate multi-agent state graph into `ragnarok` and expose endpoints on existing FastAPI instance. |
| **UI War Room View** | Commit `0f54b434` added a minimal view, while `bcd56b8e` contained the full HUD War Room | Both sets of components exist in `src/frontend/components/views/` and `src/frontend/components/hud/` | Restore full multi-tab HUD view to `/war-room` and wire to the backend. |
