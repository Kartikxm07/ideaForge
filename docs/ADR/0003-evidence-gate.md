# ADR 0003: Separate model proposals from source evidence checks

Status: accepted for the local analysis milestone.

Ollama may propose contract findings, but its output is untrusted. The worker limits source context, validates the response schema, checks every quoted substring under its claimed heading, and rechecks source hashes before committing. A failed citation rejects that candidate. Accepted records are called `EVIDENCE_CHECKED` to describe the test actually performed; their legal interpretation still requires a human and effective-term analysis. A narrow deterministic uptime comparison offers an explicit offline path when no model is installed.
