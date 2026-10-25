# ODIN integration plan

Phase 1 proposal · 25 October 2026 · approval pending.

## Decisions

1. **Extend the existing Next.js application.** The latest prompt explicitly prioritizes existing UI/API contracts over the earlier Vite request. Keep `src/frontend`, App Router, existing component library and Better Auth scaffold. Add a typed server-state adapter and page shell. The experimental `src/odin-web` is inactive; no further investment is planned without an explicit framework change.
2. **Use LangGraph for the multi-agent router**, with SQLite as the authoritative shared store. LangGraph is installed and fits the requested bounded state transitions. Persist node inputs/outputs/messages before transitions; its graph/checkpoint layer must not become a second source of truth. Reuse worker leases and idempotency patterns. Add declared, tested dependency versions during Phase 2. A hand-written graph remains a fallback only if deployment constraints prevent LangGraph.
3. **Keep Claude as the only LLM provider.** Retain heavy/light env configuration; explicit timeout, temperature, bounded retries, one repair, schema/citation gates, usage accounting and response cache. Remove misleading Ollama configuration paths in a compatibility-conscious cleanup. Deterministic code and mocked providers remain available for tests and are not alternative live LLM providers.
4. **Preserve existing APIs.** Add a versioned multi-agent namespace rather than silently changing the narrow `/analyses` behavior or reusing generic task events as agent messages. Stable adapters translate persisted domain rows into the existing UI types.
5. **Use a server-side authenticated bridge.** Better Auth session is checked in Next.js route handlers; backend bearer credentials stay server-side. Initially preserve the local single-owner runtime. Do not imply tenant isolation by forwarding arbitrary browser org IDs. Real organizations need explicit server-verified membership-to-owner mapping and tests before release.
6. **Source-backed calculations only.** Decimal monetary values, currency, formula, source citations, applicable effective dates and event provenance travel together. Preserve exact quotations/offsets. Missing holidays, clock or event files yield explicit incomplete reasons, not seeded guesses.

## Visual direction retained from the user's screenshot

Use one semantic token system across login and all dashboards: deep navy primary/navigation selection, muted gold ODIN emblem, white cards, pale blue-gray page/sidebar, thin cool borders and restrained red/amber/green/blue statuses. Retain DM Sans/Inter unless visual testing warrants a change. The UI/UX skill informed contrast, focus, readable density and responsive checks; the supplied screenshot governs composition and palette.

Login: split layout with original or licensed dark mountain artwork and a gold emblem; white form panel; actual email/password sign-in; password reveal; real session restoration. No fake credentials, unsupported recovery/OAuth controls, invented activity or sample portfolio counts. Existing image provenance must be checked before reuse. Do not copy the reference's numerical examples as product data.

Dashboard: slim light sidebar, compact topbar/search/profile, title/date/actions, metric row, risk donut and deadline list, five specialist cards, exposure and activity. Implement useful unknown/empty states where backend outputs are absent. Contracts use a filterable paginated table and a two-column clause/source viewer. Timeline uses backend checkpoint data. Mobile uses accessible drawer navigation and single-column cards. Motion is subtle and respects reduced motion.

## Proposed additions

```text
ragnarok/
  agents/
    schemas.py                 typed outputs and hand-off envelopes
    prompts/                   separate Thor/Loki/Heimdall/Tyr/synthesis prompts
    thor.py, loki.py, heimdall.py, tyr.py, synthesis.py
  orchestration/
    graph.py                   Odin routing; no domain extraction
    state.py                   run/checkpoint/workstream references
    worker.py                  durable claims, retries, cancellation
    completeness.py            evidence and unfinished-work gates
  domain/
    ingest.py, clock.py         verified pack schemas and input provenance
    citations.py               source spans, exact/normalized verdicts
    calc.py                    Decimal, dates, holidays, tiers
    terms.py                   incorporation/amendment precedence
    timeline.py                deterministic Norns projections
  inference/
    claude.py, budget.py        schema, repair, caching, accounting
  multiagent_api.py            additive API adapter
  migrations/                  additive, reviewed SQLite migrations
src/frontend/
  app/api/odin/[...path]/       authenticated server proxy, bounded allowlist
  app/(workspace)/             shared sidebar/topbar + required route pages
  components/hud/, views/, ui/  reuse and restyle existing components
  lib/api/, lib/queries/        validated typed client and server state
  store/useOdinStore.ts         UI controls only; no authoritative server data
tests/
  test_calc.py, test_ingest.py, test_citations.py
  test_agents.py, test_router.py, test_completeness.py
  test_api_contracts.py, test_acceptance.py
```

Names are proposed, not claims that these files already exist. Avoid collision with existing `events`, `findings`, `analysis_runs` and task tables: use `ma_` prefixes or new explicitly versioned tables with owner/run/checkpoint scope, and adapters for legacy records.

Store every entity in section 4 of the new prompt: documents/clause indices, workstreams, extractions, effective terms, event mappings, alerts, timeline/exposure, findings, clarifications, verifications, rulings, actions, messages, LLM calls/cache, snapshots, reports and parse errors. Capture input hashes, model/config versions, lease ownership and attempt identities. Approval should bind to the exact draft revision and evidence hashes. No sending integration is included.

## Additive endpoint plan

All paths below are proposed under `/api/v1/odin`; existing `/api/v1` resources remain compatible.

| Endpoint | Purpose / owning phase |
| --- | --- |
| `GET /capabilities` | Implemented providers, upload formats, limits, status vocabularies; Phase 2 |
| `POST /ingestions`, `GET /ingestions/{id}` | Bounded file/bundle ingestion with warnings/quarantine; Phase 2 |
| `GET /documents/{id}/clauses`, `GET /clauses/{id}` | Stable IDs, exact text, source hash/offset; Phase 2 |
| `POST /runs`, `GET /runs`, `GET /runs/{id}`, `POST /runs/{id}/cancel` | Durable full pipeline start/status/cancel; Phase 6 |
| `GET /runs/{id}/workstreams`, `/extractions`, `/effective-terms` | Observable plan and grounded terms; Phase 3 |
| `POST /runs/{id}/clarifications` | Targeted clause-only requests, bounded/cached; Phase 3 |
| `GET /runs/{id}/clock`, `POST /runs/{id}/simulate` | Source-defined dates and deterministic recalculation; Phase 4 |
| `GET /runs/{id}/snapshots?at=`, `/timeline?at=`, `/exposure?at=` | Checkpoint-specific views and formulas; Phase 4 |
| `GET /runs/{id}/findings`, `/verifications`, `/rulings`, `/messages` | Debate and provenance; Phase 5 |
| `GET /runs/{id}/actions`, `PATCH /actions/{id}` | View/edit draft; optimistic revision checks; Phase 5/6 |
| `POST /actions/{id}/approve`, `/reject`, `/request-revision` | Human review with audit and no dispatch; Phase 6 |
| `GET /runs/{id}/alerts`, `PATCH /alerts/{id}` | Persisted acknowledgement/review/resolution; Phase 6 |
| `GET /runs/{id}/stream?after=` | Resumeable ordered SSE with heartbeat/reconnect/cleanup; Phase 6 |
| `GET /runs/{id}/reports`, `GET /reports/{id}` | Stored contract/company reports and completeness; Phase 6 |
| `GET /runs/{id}/graph`, `/dashboard`, `/agents`, `/llm-calls` | Views projected from stored rows; Phase 6/7 |
| `GET /search?q=`, `GET /notifications` | Scoped grouped search and persisted alerts/approvals; Phase 7 |

Pagination should use a consistent envelope. Mutations accept idempotency or revision tokens as appropriate. Stream event IDs come from persisted messages, not invented elapsed-time progress. Server state uses TanStack Query; presentation-only selections can remain in Zustand. Expose concise decision summaries, not hidden chain-of-thought.

## Phase gates

| Phase | Work | Validation / stop condition |
| --- | --- | --- |
| 1 | Reconnaissance and these two documents | User confirms plan with “go next”; pack location remains required for source-specific checks |
| 2 | Fix dependency/config/test drift; deterministic foundations, typed store, input loaders, Claude wrapper/budgets | Unit tests and ingestion demo; source-specific clock/ledger/event checks cannot pass until files are available |
| 3 | Odin plan, per-contract Thor, targeted clarification, effective terms | Every accepted extraction cited; rejection logging; dual amendment provenance; cache assertions |
| 4 | Heimdall event mapping and deterministic Norns/checkpoint snapshots | Temporal visibility, holiday/credit/notice calculations, formula-bearing exposure |
| 5 | Loki, independent Heimdall checks, Tyr, bounded router and drafts | Forced disagreement/loop limits, correct evidence gates, draft recipient/signatory validation |
| 6 | Durable full pipeline, completeness, synthesis, additive API | Reproducibility, forced-failure INCOMPLETE, source scan of all citations, correct exposure aggregation |
| 7 | Existing UI integration and screenshot-aligned polish | Real-backend E2E, responsive/accessibility checks, T1–T16 with evidence/discrepancies, acceptance report and run/demo guides |

Stop and report after every phase. Mocked inference keeps automated tests independent of paid live calls. Tests may use synthetic fixtures explicitly labeled as synthetic; they must never be reported as passing organizer-pack acceptance.

## Risks and prerequisites

- **Missing pack:** need its actual local path (or a supplied copy) containing the format spec, clock, events, ledger, holidays and originals. Stored contract text can support preliminary work, but cannot recreate missing event history or holiday rules.
- **Broken baseline:** Python suite currently has 11 configuration-fixture failures; frontend has 24 TypeScript diagnostics. Correct in Phase 2 without discarding existing edits. Re-run to reveal subsequent failures.
- **Fresh-clone dependencies:** Anthropic is not declared; LangGraph also needs a tested declared version. Better Auth currently needs PostgreSQL and auth environment variables. “Only ANTHROPIC_API_KEY” is not currently enough: provide explicit bootstrap/config generation and either documented local Postgres provisioning or a reviewed auth-storage adapter.
- **Identity bridge:** Next.js account sessions and Python owner-token authorization are separate systems. Do not forward the global token on an unauthenticated proxy. Verify membership and scope before adding organizations.
- **Source discrepancies:** sector-specific exclusivity, unset go-live date, incident credit conditions, invoice timing and changing monthly fees must remain explicit. Do not tune the engine to the expected-answer table.
- **Existing fake source claims:** report-page citations conflict with actual A3 text. Remove production mock fallbacks during integration, preserve sample-only fixtures for testing, and never label fabricated reports complete.
- **Embedded credential literal:** the old login source contains a bearer-token default and localStorage logic. Remove this path during auth integration; if that value is a real deployed credential, rotate it. No credential values are reproduced in these deliverables.
- **Draft work from earlier request:** `web_auth.py`, `workspace_api.py`, migration 006 and Vite scaffold are disconnected. Do not activate them wholesale; they do not meet the requested multi-agent architecture. Keep them available until deciding whether to reuse small pieces or remove them, preserving unrelated edits.

## Checks performed and reproducible commands

```powershell
# From repository root; these checks make no paid model calls.
python -m compileall -q ragnarok
python -m pytest -q --tb=no
& src/frontend/node_modules/.bin/tsc.cmd --noEmit --incremental false -p src/frontend/tsconfig.json
```

Compile passed; pytest returned 2 passes / 11 failures; TypeScript emitted 24 diagnostics. No feature/E2E success is claimed. No persistent database migration, live Claude inference, commit, deployment, or notice delivery was performed.

Phase 1 is ready for review; Phases 2–7 have not started under this new gated plan.
