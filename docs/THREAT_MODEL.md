# Threat model

## Assets and boundaries

Assets are the bearer token, local prompts, plans, memories, workflow results, and audit records. The local client is untrusted at the API boundary. Ollama output is untrusted at the planner boundary. The worker is trusted code, while tool arguments require schema validation and application authorization. The file system and host account are outside this service's protection.

## Threats and current controls

| Threat | Current control | Remaining risk |
| --- | --- | --- |
| Remote API access | CLI binds to `127.0.0.1`; bearer token required on private routes | A same-host process can attempt access; no TLS or rate limit |
| Prompt injection asks for a dangerous tool | Tool IDs are checked against a closed registry; model cannot grant approval | Future tools need independent review and sandboxing |
| Unapproved memory write | SHA-256 digest binds approval to the exact step specification; checked again by worker | No interactive approval UI yet |
| Cross-owner read or deletion | Every task and memory query is owner-filtered | Owner ID is an environment setting, not a full identity system |
| Duplicate execution after crash | SQLite transaction, lease, completed-step skip, deterministic memory ID | Only built-in idempotent tools are allowed; no external side effects |
| SSRF or cloud prompt leakage | Ollama URL validation restricts to loopback; `trust_env=False`; no cloud fallback | A compromised local Ollama process can still see prompts |
| Secret leakage | Token comes from environment and is not logged | No secret manager; local operators must protect environment and database |
| Malicious manifest path | Resolved paths must remain inside the chosen bundle; only `.txt` contract and company files are read | Source text is untrusted and must not become instructions to later agents |
| Fabricated legal citation | Exact quote and heading are checked against stored source text and its hash | This verifies text location, not legal reasoning or current contractual effect |
| Model-generated false legal conclusion | Model output is typed, bounded, and stored as a candidate with an evidence-only status | A human reviewer and effective-term engine are still required |
| Stale source cited as current | Hashes captured at run creation and rechecked before commit; updates mark findings stale | External copies and exports must retain source hashes |

The current runtime is suitable for local development and demonstrations, not untrusted public multi-user hosting. Before adding SaaS access: use independent identity verification, tenant membership checks, rate limiting, CSRF-safe browser auth, TLS, abuse controls, encryption key management, and deeper security testing.

