# Architecture

## Current implementation

At initial assessment, the linked GitHub repository had only a short README. During implementation it gained an ODIN architecture roadmap README, which this change preserves. The local workspace also contained `docs/Pack/odin_dev_pack`, a fictional contract challenge dataset, and `docs/Odin_PS.pdf`. Those files are preserved. No previous application code, database, frontend, tests, or deployment system existed.

```mermaid
flowchart LR
  User[Local user] -->|Bearer token, loopback| API[FastAPI API]
  API --> DB[(SQLite task, event, memory ledger)]
  API -->|Explicit planning request only| Ollama[Loopback Ollama]
  Worker[Local worker] --> DB
  Worker --> Tools[Closed built-in tool registry]
  Tools --> DB
```

The local runtime owns prompts, plans, memories, approvals, events, source documents, and audit records. API handlers validate requests and owner scope. The worker claims one step at a time with a lease, records its state before execution, and persists the result. Completed steps are skipped after a restart. The available tools are pure text operations and a transactional memory write. There is no arbitrary shell, file, or web tool. Document ingestion is an explicit local CLI or API operation; source text is not sent to Ollama automatically.

An analysis run selects one to three owned documents and a focus phrase. The worker builds bounded excerpts, then invokes the configured local provider. Proposed citations are checked against the current source text and heading inside a transaction. Unsupported proposals are counted as rejected. Findings record the source hash and are labeled `EVIDENCE_CHECKED`; source changes mark them stale. A narrow deterministic uptime comparison supports offline demonstrations. See [ADR 0003](ADR/0003-evidence-gate.md).

Operational events have a separate owner-scoped ledger. Each event has a stable source ID and normalized UTC timestamp. JSONL imports validate records before writing, skip exact duplicates, reject changed content for the same ID, and quarantine malformed lines without storing their raw text in the error table. Checkpoint queries filter by end-of-day UTC.

This is a single-user local runtime with an owner identifier for data isolation tests. It does not offer real multi-user authentication or a cloud control plane. The API is bound to loopback by the CLI. Directly deploying it to a public network is unsupported.

## Decisions

- [ADR 0001](ADR/0001-local-runtime.md): Start with a local FastAPI runtime and SQLite ledger.
- [ADR 0002](ADR/0002-bounded-tools.md): Restrict execution to reviewed built-in tools.

## Next architecture step

Add a separately deployable control plane with independent identity, organization membership, and runtime registration. All cloud synchronization must be opt-in metadata with a documented schema. Private content remains local unless a user explicitly authorizes transfer.

