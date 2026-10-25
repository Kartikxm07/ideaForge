# ODIN repository reconnaissance

Phase 1 report · 25 October 2026 · awaiting user confirmation.

## Scope and instruction precedence

The latest attached **ODIN MASTER BUILD PROMPT** requests seven gated phases, preservation of the existing UI/API, Claude-only inference, and no feature implementation in Phase 1. It supersedes the earlier instruction to immediately build a Vite frontend. The user's supplied screenshot remains the visual target. No new feature implementation was performed after reading the latest prompt; earlier experimental API wiring was disconnected to restore the original runtime behavior.

Workspace: `C:/Users/athar/OneDrive/Desktop/ragnarork`.

Git remotes: `origin` is `https://github.com/Kartikxm07/ideaForge.git`; `ragnarok` is `https://github.com/Kartikxm07/Ragnarok.git`. The claim that this is the organizer's original repository is not established by the remote names. No clone/fetch/push was performed.

## Structure and execution

| Area | Actual implementation | Entry points |
| --- | --- | --- |
| Backend | Python, FastAPI, Pydantic, synchronous SQLite transactions | `ragnarok/api.py`, `cli.py`, `store.py` |
| Worker | Explicit bounded tool workflow plus separate single-proposal analysis workflow | `workflow.py`, `analysis.py` |
| Inference | Anthropic SDK, ClaudeProvider; old OllamaProvider name aliases ClaudeProvider | `model.py` |
| Frontend | Next.js 16.1.1 App Router, React 19.2.3, TypeScript, Tailwind 4, Zustand | `src/frontend` |
| UI libraries | shadcn/Radix/Base UI, Lucide, Framer Motion, Recharts | `src/frontend/package.json`, `components/ui` |
| Account scaffold | Better Auth + Drizzle + PostgreSQL | `lib/auth.ts`, `lib/db`, `/api/auth/[...all]` |
| Tests | pytest; temporary SQLite databases; in-process HTTPX ASGI requests | `tests/test_local_runtime.py` |
| CI | Python 3.11 and 3.13; editable install, compileall, pytest | `.github/workflows/ci.yml` |
| Package managers | pip/setuptools for Python; npm scripts for frontend | `pyproject.toml`, `src/frontend/package.json` |

Backend commands: `python -m ragnarok.cli api`, `worker`, `migrate`, `doctor`, `ingest-odin --bundle PATH`, and `ingest-events --file PATH`. API binds to `127.0.0.1:8000`. `doctor` invokes provider health and may access Anthropic; it was not run during reconnaissance.

Frontend scripts: `npm run dev`, `build`, `start`, `lint`, `db:push`, `db:generate`, `db:studio` from `src/frontend`. The documented UI address is `http://localhost:3000`. No service was started and no auth database push was performed.

## Primary data availability

The original `02_Ragnarok Odin The Contract War Room/Pack/odin_dev_pack` directory is **not present at the supplied workspace-relative path**. Searches of the workspace, Desktop, and targeted neighboring project directories did not locate the pack's format specification, clock, manifest, events, ledger or holidays files. Historical docs refer to `docs/Pack/odin_dev_pack` and `docs/Odin_PS.pdf`; those paths are absent here.

The existing, ignored `data/ragnarok.sqlite3` contains nine imported source documents. It was inspected in SQLite read-only mode, without migrating or changing it. Schema version is **5**. Counts: documents **9**, operational events **0**, analysis runs **0**, findings **0**. All nine source-content hashes match the stored SHA-256 values. This confirms internal integrity, not authenticity against the unavailable original files.

| Stored key | Recorded source path | Characters | Content/format observed |
| --- | --- | ---: | --- |
| STD | `bundle:contracts/STD.txt` | 26,328 | Common Paper standard terms, numbered sections and clauses |
| A1 | `bundle:contracts/A1.txt` | 6,887 | StratoNode cover page, lettered sections, fees, notice addresses, incorporation |
| A2 | `bundle:contracts/A2.txt` | 5,783 | StratoNode SLA, numeric clauses, ASCII credit table |
| A3 | `bundle:contracts/A3.txt` | 4,881 | Amendment, replacement clauses, explicit effective date |
| B1 | `bundle:contracts/B1.txt` | 9,961 | Harbor cover page, lettered headings and `§3.1`-style clauses |
| B2 | `bundle:contracts/B2.txt` | 8,752 | Harbor DPA; explicit missing-exhibits note |
| C1 | `bundle:contracts/C1.txt` | 7,896 | Vantage agreement; effective date not filled in |
| D1 | `bundle:contracts/D1.txt` | 15,610 | Pixelwright contractor agreement; numbered clauses and milestone table |
| company-context | `bundle:company/context.txt` | 3,209 | Plain-text organizational facts, signatories, addresses, insurance |

These are database provenance strings, **not files currently on disk**. PDF originals and source-page mappings are unavailable. Unicode text includes section signs, punctuation, and mathematical symbols; console output needs UTF-8. A Windows console encoding failure occurred during one read; subsequent reads used UTF-8. Source content was not altered.

### Other input formats

- Manifest: code expects JSON `{files: [{path, title, ...}]}`, at most 100 files. Paths must resolve inside the selected bundle; only `.txt` under `contracts/` and `company/` are imported. This is an implementation contract, not a verified organizer specification.
- Events: code expects JSONL records with `event_id`, timezone-aware `timestamp`, `channel`, `from`, `to`, `subject`, `body`. Valid events are normalized to UTC; duplicate IDs with identical content are skipped; changed content is rejected. Malformed lines are quarantined by source file, line number, hash and error type. No source event lines are available to inspect, so the malformed-line count in the latest prompt is unverified.
- Clock: unavailable; the actual schema and checkpoints cannot be verified. Frontend mock dates are not authoritative.
- Ledger and holidays: unavailable; neither actual CSV headers nor holiday conventions can be established. No current ingestion/calculation implementation exists for them.
- Organizer format and submission requirements: unavailable. The prompt and old implementation notes are secondary evidence, not replacements for the pack.

## Source constraints and discrepancies

Existing repository rules worth retaining:

1. README: **“Every important finding must be explainable.”** It requires the source-to-action evidence trail and distinguishes forecasts from facts.
2. Runtime guide: **“Findings marked `EVIDENCE_CHECKED` have verified quote locations, not verified legal conclusions.”** Do not map this status to confirmed breach or Heimdall verification.
3. ADR 0003: **“A failed citation rejects that candidate.”** Preserve source hash rechecks and stale-source handling.
4. API docs: **“All `/api/v1` routes require `Authorization: Bearer <RAGNAROK_API_TOKEN>`.”** Existing authenticated clients must remain compatible.
5. ADR 0001: **“A separate worker prevents long work from running in request handlers.”** Extend the durable worker, not request-scoped background execution.

These docs are project rules; organizer authorship is not established. Older docs also describe loopback Ollama and no cloud transfer, but current locally modified code calls Claude. The latest user prompt explicitly authorizes Claude. Documentation must be reconciled in Phase 2.

Observed source facts relevant to later acceptance tests:

- A2 §2.1 gives 99.5% uptime; B1 §3.1 gives 99.9%. A1 gives an $8,000 monthly fee; B1 gives $40,000 initially, increasing to $41,200 from September 15, 2027. Calculations must use the applicable date.
- A3 replaces the request window with 15 days and changes non-renewal to 60 days, effective January 1, 2027. Its additional 5% incident credit must be interpreted separately from baseline SLA eligibility; do not force the acceptance table's March recovery assumption.
- B1 §8.1 explicitly requires consecutive missed months. §8.2 ties the 15-day insurance cure period to written notice, not automatically to policy expiry.
- B2 explicitly says Exhibits A and B were not included. Flag incomplete; do not generate the exhibits.
- C1's effective date is `[TO BE INSERTED UPON GO-LIVE]`. Do not substitute the signature date or a mock date.
- B1 §6.1 restricts Enterprise in the retail grocery sector; C1 §4.1 restricts all tiers in the third-party logistics sector. Geographic overlap alone does not prove a conflict. Sector overlap needs evidence.
- D1 §4.2 requires ten business days excluding the supplied company holidays; §4.3 defines deemed acceptance. M4 is $12,000, but §3.2 makes invoicing and payment separate steps. Deemed acceptance must not be labeled immediate overdue payment without invoice evidence.
- D1 §10.6 requires an amendment signed by both parties. STD §12.4 requires written notices to the specified notice address.
- Stored titles say “Harbor Retail Solutions LLC” while agreement text identifies “Harbor Retail Group LLC”; C1 metadata abbreviates Corp. while source uses Corporation. Keep metadata and source identities distinct and flag mismatches.
- Source events, checkpoint dates, incident durations, ledger discrepancies, actual insurance lapse, and delivery dates in T2/T3/T5/T7/T9/T10–T15 remain unverified here.

## Existing UI and integration map

There is no contract API client in the existing frontend. Domain views read mock arrays through `store/useOdinStore.ts`; mutations alter browser memory. Better Auth has a real server route, but the ODIN login page does not call it.

| Page/component | Present behavior | Integration needed |
| --- | --- | --- |
| `/` | Redirects to `/login` | Preserve redirect with real session handling |
| `/login` | Timer-based simulated success; embedded token value and localStorage token path | Replace with Better Auth sign-in; no embedded credentials or long-lived browser bearer storage |
| `/onboarding`, `/new-case` | Local form/file collection | Persist company context, bundle/doc ingestion |
| `/war-room` | Simplified dashboard, hardcoded financial metrics; reads nonexistent `nodes` / `timelineEvents` | Restore typed data selectors and server metrics |
| `/analysis` | Hardcoded stages, counts and budget | Durable run status/messages/budget observations |
| `/reports` | Hardcoded narrative and citations | Persisted reports with completeness and verified source references |
| `PlanView` | Hardcoded workstreams and progress | Odin workstream records |
| `ContractGraphView` | Custom graph/card display, Zustand contract/edge arrays | Persisted dependencies, clause/party nodes; interactive graph adapter |
| `TimeSlider`, `TimelineView` | Browser clock and mock checkpoint selection | Server simulation/snapshot query, cancellation of obsolete requests |
| `ExposureView` | Mock expected/worst-case data and heatmaps | Decimal-based exposure rows with formulas/currency/assumptions |
| `DebateView` | Mock conflict arguments/verifications/rulings | Stored findings, verifications, rulings and hand-offs |
| `ActionsView` | Browser-memory approve/reject | Durable revisioned review actions; consequential confirmation |
| `TraceView` | Example execution trace | Observable message and LLM call metadata |
| `AlertFeedRightRail` | Local acknowledgement/snooze | Persisted alert state, priority ordering |
| `EvidenceDrawer`, `ClauseDiffModal` | Mock clauses/diffs/scores | Exact text, stable IDs, hashes and source offsets |
| `AddContractModal`, `AddEventModal` | Timed success; local callback/store updates | Validated persistent ingestion and processing states |

FR9 has reusable visual scaffolding for graph, timeline, exposure, debate, alerts/actions, and observability. It has **no verified end-to-end data integration**. Several components use the older dark neon theme while global CSS uses cream/gold. The reference screenshot instead calls for a pale blue-gray canvas, white cards, light sidebar/navy selected rows, gold emblem, and navy mountain login.

Current types also overstate certainty: mandatory confidence/progress, only three hardcoded checkpoint IDs, and `No Risk` without an unassessed state. Extend these types with explicit unknown/partial states while adapting existing consumers.

## Existing backend/API map

All private routes are owner-scoped. Health, models/tools, tasks, memories and audit routes are documented in `docs/API.md`.

| Resource | Existing routes and payloads |
| --- | --- |
| Documents | `GET/POST /api/v1/documents`; `GET/DELETE /documents/{key}`; POST fields `document_key,title,content` |
| Search | `GET /documents/search?q=`; returns key, title, hash, offset, snippet and heading |
| Citations | `POST /citations/verify` with key/ref/quote; returns exact-text + heading verdict, offset and hash |
| Analyses | `POST/GET /analyses`; `GET /analyses/{id}`; `POST /analyses/{id}/cancel`; question/focus/1–3 keys/provider; idempotency header |
| Operational events | `GET/POST /operational-events`, `GET/DELETE /operational-events/{id}`; date filtering via `as_of` |
| Quarantine | `GET /event-import-errors`; hashes and locations, no raw malformed payload |
| Tasks | Explicit tool steps or model plan; state, event polling, exact-digest approval and cancellation |

`analysis.py` captures hashes, selects up to four excerpts around a focus phrase per document, obtains one batch of candidate findings, verifies citations, then stores accepted findings. It is not the requested multi-agent engine. No Thor/Heimdall/Tyr agents, persisted debate, term merger, holiday calculator, portfolio snapshots or completeness gate currently exist. The task worker's leases/idempotency provide useful durable execution patterns.

Citation behavior is stricter than the new prompt's normalized quote suggestion: quote is an exact substring; heading whitespace/case is normalized and checked as a prefix; start/end must stay under the same heading. Preserve exact verdict semantics; if normalized matching is added, label it separately and preserve offsets.

## Environment and checks

| Check | Result |
| --- | --- |
| Python | 3.12.4 |
| Node / npm | v24.12.0 / 11.11.0 |
| Anthropic SDK / LangGraph / pytest import availability | All installed |
| `ANTHROPIC_API_KEY` in process env | Not set |
| Effective configuration key | Present via local `.env`; value not printed |
| Claude model access/key validity | Not tested; no paid calls made |
| Dependency manifest | Anthropic is imported but absent from `pyproject.toml`; clean install is not reproducible |
| SQLite integrity spot check | All nine document hashes match; schema 5 |
| `python -m compileall -q ragnarok` | Pass |
| `python -m pytest -q --tb=no` | **2 passed, 11 failed** after draft wiring was disconnected |
| Existing frontend TypeScript check | **24 diagnostics**, no passing typecheck |

All eleven remaining pytest failures reach the old five-argument `Settings(...)` fixture while the locally modified config now requires six arguments including `model_light`. Further failures may emerge after this first blocker is corrected. The first test run also exposed one draft schema-version regression; disconnecting that draft restored the schema upgrade test.

Frontend diagnostics include: missing `nodes`/`timelineEvents`; missing `MOCK_SNAPSHOTS`, `MOCK_CLAUSES`, `MOCK_ALERTS`, `MOCK_SWIMLANES`, `MOCK_HEATMAP`, and `HeatmapCell`; unsafe optional score/provenance access; missing timeline fields. These are present in existing user files and were not fixed during Phase 1.

## Working-tree ownership and earlier drafts

Pre-existing modified files: `README.md`, `ragnarok/{analysis,api,config,model}.py`, frontend Drizzle/Next configs, mock data and ODIN types. The login background image was already untracked. Preserve all of these.

Before the new gated prompt arrived, this chat created experimental `ragnarok/web_auth.py`, `workspace_api.py`, `migrations/006_workspace.sql`, and `src/odin-web/`. These are **unvalidated, inactive drafts**, not accepted architecture. API imports/registration and the store's migration-6 dispatch have been removed again; the real database was never migrated. The Vite scaffold lacks App/styles/test setup and is not runnable. Its npm install was interrupted when the task changed. Do not use it as the deliverable or claim any of its routes are available.

Phase 1 deliverables are this report and `INTEGRATION_PLAN.md`; no feature changes are scheduled until the user says “go next.”

## Full application file inventory

The following inventory excludes Git internals, dependency directories, caches, build artifacts, environment files, and local skill packages. Secret values and the SQLite file contents are intentionally excluded. `.agents/skills/` contains auxiliary UI/Stitch/animation instructions, not application code. The database location and newly authored Phase 1 docs are described above.

```text
.github/workflows/ci.yml
.gitignore
RAGNAROK_RUNTIME.md
README.md
docs/ADR/0001-local-runtime.md
docs/ADR/0002-bounded-tools.md
docs/ADR/0003-evidence-gate.md
docs/API.md
docs/ARCHITECTURE.md
docs/DATA_FLOW.md
docs/IMPLEMENTATION_PLAN.md
docs/TESTING.md
docs/THREAT_MODEL.md
pyproject.toml
ragnarok/__init__.py
ragnarok/analysis.py
ragnarok/api.py
ragnarok/cli.py
ragnarok/config.py
ragnarok/documents.py
ragnarok/migrations/001_init.sql
ragnarok/migrations/002_documents.sql
ragnarok/migrations/003_analysis.sql
ragnarok/migrations/004_operational_events.sql
ragnarok/migrations/005_event_import_errors.sql
ragnarok/migrations/006_workspace.sql
ragnarok/model.py
ragnarok/operational_events.py
ragnarok/store.py
ragnarok/tools.py
ragnarok/web_auth.py
ragnarok/workflow.py
ragnarok/workspace_api.py
skills-lock.json
src/frontend/.devcontainer/Dockerfile
src/frontend/.devcontainer/devcontainer.json
src/frontend/.devcontainer/docker-compose.yml
src/frontend/.github/dependabot.yml
src/frontend/README.md
src/frontend/RELEASE.md
src/frontend/app/analysis/page.tsx
src/frontend/app/api/auth/[...all]/route.ts
src/frontend/app/favicon.ico
src/frontend/app/globals.css
src/frontend/app/layout.tsx
src/frontend/app/login/page.tsx
src/frontend/app/new-case/page.tsx
src/frontend/app/onboarding/page.tsx
src/frontend/app/page.tsx
src/frontend/app/reports/page.tsx
src/frontend/app/war-room/page.tsx
src/frontend/components.json
src/frontend/components/auth-section.tsx
src/frontend/components/component-example.tsx
src/frontend/components/example.tsx
src/frontend/components/hud/AddContractModal.tsx
src/frontend/components/hud/AddEventModal.tsx
src/frontend/components/hud/AlertFeedRightRail.tsx
src/frontend/components/hud/ClauseDiffModal.tsx
src/frontend/components/hud/EvidenceDrawer.tsx
src/frontend/components/hud/HudHeader.tsx
src/frontend/components/hud/KpiStrip.tsx
src/frontend/components/hud/TimeSlider.tsx
src/frontend/components/ui/accordion.tsx
src/frontend/components/ui/alert-dialog.tsx
src/frontend/components/ui/alert.tsx
src/frontend/components/ui/aspect-ratio.tsx
src/frontend/components/ui/avatar.tsx
src/frontend/components/ui/badge.tsx
src/frontend/components/ui/breadcrumb.tsx
src/frontend/components/ui/button-group.tsx
src/frontend/components/ui/button.tsx
src/frontend/components/ui/calendar.tsx
src/frontend/components/ui/card.tsx
src/frontend/components/ui/carousel.tsx
src/frontend/components/ui/chart.tsx
src/frontend/components/ui/checkbox.tsx
src/frontend/components/ui/collapsible.tsx
src/frontend/components/ui/combobox.tsx
src/frontend/components/ui/command.tsx
src/frontend/components/ui/context-menu.tsx
src/frontend/components/ui/dialog.tsx
src/frontend/components/ui/drawer.tsx
src/frontend/components/ui/dropdown-menu.tsx
src/frontend/components/ui/empty.tsx
src/frontend/components/ui/field.tsx
src/frontend/components/ui/hover-card.tsx
src/frontend/components/ui/input-group.tsx
src/frontend/components/ui/input-otp.tsx
src/frontend/components/ui/input.tsx
src/frontend/components/ui/item.tsx
src/frontend/components/ui/kbd.tsx
src/frontend/components/ui/label.tsx
src/frontend/components/ui/menubar.tsx
src/frontend/components/ui/navigation-menu.tsx
src/frontend/components/ui/pagination.tsx
src/frontend/components/ui/popover.tsx
src/frontend/components/ui/progress.tsx
src/frontend/components/ui/radio-group.tsx
src/frontend/components/ui/resizable.tsx
src/frontend/components/ui/scroll-area.tsx
src/frontend/components/ui/select.tsx
src/frontend/components/ui/separator.tsx
src/frontend/components/ui/sheet.tsx
src/frontend/components/ui/sidebar.tsx
src/frontend/components/ui/skeleton.tsx
src/frontend/components/ui/slider.tsx
src/frontend/components/ui/sonner.tsx
src/frontend/components/ui/spinner.tsx
src/frontend/components/ui/switch.tsx
src/frontend/components/ui/table.tsx
src/frontend/components/ui/tabs.tsx
src/frontend/components/ui/textarea.tsx
src/frontend/components/ui/toggle-group.tsx
src/frontend/components/ui/toggle.tsx
src/frontend/components/ui/tooltip.tsx
src/frontend/components/views/ActionsView.tsx
src/frontend/components/views/ContractGraphView.tsx
src/frontend/components/views/DebateView.tsx
src/frontend/components/views/ExposureView.tsx
src/frontend/components/views/PlanView.tsx
src/frontend/components/views/TimelineView.tsx
src/frontend/components/views/TraceView.tsx
src/frontend/drizzle.config.ts
src/frontend/drizzle/0000_colossal_emma_frost.sql
src/frontend/drizzle/meta/0000_snapshot.json
src/frontend/drizzle/meta/_journal.json
src/frontend/eslint.config.mjs
src/frontend/hooks/use-mobile.ts
src/frontend/lib/auth-client.ts
src/frontend/lib/auth.ts
src/frontend/lib/db/client.ts
src/frontend/lib/db/schema/auth-schema.ts
src/frontend/lib/db/schema/index.ts
src/frontend/lib/utils.ts
src/frontend/mock/odinData.ts
src/frontend/next-env.d.ts
src/frontend/next.config.ts
src/frontend/package.json
src/frontend/postcss.config.mjs
src/frontend/public/file.svg
src/frontend/public/globe.svg
src/frontend/public/next.svg
src/frontend/public/odin_login_bg.jpg
src/frontend/public/vercel.svg
src/frontend/public/window.svg
src/frontend/store/useOdinStore.ts
src/frontend/tsconfig.json
src/frontend/types/odin.ts
src/odin-web/index.html
src/odin-web/package.json
src/odin-web/src/api.ts
src/odin-web/src/live.ts
src/odin-web/src/main.tsx
src/odin-web/src/ui.tsx
src/odin-web/tsconfig.json
src/odin-web/vite.config.ts
tests/test_local_runtime.py
```

