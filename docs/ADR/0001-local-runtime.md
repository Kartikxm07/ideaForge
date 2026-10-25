# ADR 0001: Local runtime first

Status: accepted for the first milestone.

The GitHub repository had no application to preserve. We chose one FastAPI service and a SQLite worker ledger because they provide a testable local-first vertical slice with minimal operational burden. The database schema has an explicit version and migration file. A separate worker prevents long work from running in request handlers. Postgres, Redis, Temporal, and a cloud control plane would add operational complexity before their contracts are defined. This decision does not preclude later adapters.

