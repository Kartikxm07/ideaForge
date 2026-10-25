"""Focused regressions for uploaded contract validation and long source handling."""
import json
from types import SimpleNamespace

import pytest

from ragnarok.agents import contract_warning, execute_run, run_view, start_run, thor_chunks
from ragnarok.documents import upsert_document
from ragnarok.store import Store


class ShortFakeModel:
    settings = SimpleNamespace(model_heavy="test")

    def __init__(self):
        self.thor_calls = 0

    def _call(self, prompt, _model, _limit):
        if "You are Thor" in prompt:
            self.thor_calls += 1
            chunk = prompt.split("\nText:\n", 1)[1]
            lines = [line for line in chunk.splitlines() if line and not line.startswith("Section ")]
            quote = lines[0]
            heading = next(line for line in chunk.splitlines() if line.startswith("Section "))
            citation = {"document_key": "LONG", "clause_ref": heading, "quote": quote}
            return json.dumps({"items": [{"field": "payment", "value": quote, "confidence": 0.9, "ambiguity": None, "citation": citation}]})
        if "You are Loki" in prompt:
            return '{"findings":[]}'
        raise AssertionError("Unexpected model stage")


def test_network_transcript_is_not_analyzed(tmp_path):
    transcript = "athar@eth:~$ nping --tcp -p 80\nnping: unrecognized option\n" * 1000
    assert "network scan" in contract_warning(transcript)
    store = Store(tmp_path / "db.sqlite3")
    store.migrate()
    upsert_document(store, "org", "ip-s", "ip's.txt", transcript, "test")
    with pytest.raises(ValueError, match="network scan"):
        start_run(store, "org", ["ip-s"])


def test_long_contract_is_chunked_and_runs(tmp_path):
    content = "Section 1. Payment\nCustomer shall pay $500 on 2027-03-15.\n" + ("The payment obligation remains subject to the written agreement.\n" * 800)
    content += "Section 2. Renewal\nThe agreement renews on 2028-03-15.\n"
    chunks = thor_chunks(content)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 20_000 for chunk in chunks)
    assert "The agreement renews on 2028-03-15." in chunks[-1]
    store = Store(tmp_path / "db.sqlite3")
    store.migrate()
    upsert_document(store, "org", "LONG", "Long agreement", content, "test")
    run = start_run(store, "org", ["LONG"])
    model = ShortFakeModel()
    execute_run(store, "org", run["id"], model)
    result = run_view(store, "org", run["id"])
    assert model.thor_calls == len(chunks)
    assert result["status"] == "COMPLETE"
    assert len(result["extractions"]) == len(chunks)
