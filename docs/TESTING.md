# Testing

Install the development dependencies and run the deterministic suite:

```powershell
python -m pip install -e '.[test]'
python -m compileall -q ragnarok
python -m pytest -q
```

The tests use temporary SQLite databases and an in-process ASGI client. They cover owner scope, token enforcement, approval binding, idempotency, worker restart, schema upgrade, document deletion and stale findings, exact citations, unavailable models, deterministic uptime comparison, event-drop duplicates, checkpoint filtering, and malformed-line quarantine. They do not require Ollama or the Odin pack. The pack smoke test is manual because those source files are not committed to this repository.

No live Ollama inference or production deployment test has passed in this environment. The CI workflow runs the deterministic suite on Python 3.11 and 3.13.
