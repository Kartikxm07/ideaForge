from pathlib import Path

from ragnarok.api import create_app
from ragnarok.config import Settings
from ragnarok.documents import import_odin_bundle
from ragnarok.odin.engine.event_parser import EventParser
from ragnarok.odin.engine.ingest import DocumentIngestor
from ragnarok.store import Store
from test_local_runtime import HEADERS, LocalClient, TOKEN


def test_overview_uses_persisted_owner_scoped_data_and_checkpoint(tmp_path):
    path = tmp_path / "odin.sqlite3"
    store = Store(path)
    store.migrate()
    bundle = Path(__file__).resolve().parents[1] / "odin_dev_pack"
    import_odin_bundle(store, "alice", bundle / "bundle")
    with store.connect() as db:
        assert len(DocumentIngestor(db, "alice").ingest_bundle(bundle)) == 8
        parser = EventParser(db, "alice")
        parser.parse_file(bundle / "bundle" / "events" / "events_drop1.jsonl")
        parser.parse_file(bundle / "bundle" / "events" / "events_drop2.jsonl")
    alice = LocalClient(create_app(Settings(TOKEN, "alice", path, "http://127.0.0.1:11434", "missing")))
    bob = LocalClient(create_app(Settings(TOKEN, "bob", path, "http://127.0.0.1:11434", "missing")))
    route = "/api/v1/odin/overview?checkpoint=2027-03-15"
    assert alice.get(route).status_code == 401
    assert alice.get("/api/v1/odin/overview?checkpoint=invalid", headers=HEADERS).status_code == 422
    first = alice.get(route, headers=HEADERS)
    assert first.status_code == 200
    body = first.json()
    assert len(body["documents"]) == 8
    assert body["documents"][0]["doc_id"] == "A1"
    assert body["clauses"] and body["clauses"][0]["body"]
    assert body["events"] and all(event["timestamp"][:10] <= "2027-03-15" for event in body["events"])
    assert body["exposure"] == body["findings"] == body["alerts"] == body["actions"] == []
    assert body["sla_scenarios"] == []  # March has not ended at the first checkpoint.
    later = alice.get("/api/v1/odin/overview?checkpoint=2027-09-15", headers=HEADERS).json()
    assert len(later["events"]) > len(body["events"])
    assert [(row["month"], row["gross_customer_credit"], row["potential_provider_credit"])
            for row in later["sla_scenarios"]] == [("2027-03", 6000, 0), ("2027-05", 6000, 2400)]
    for scenario in later["sla_scenarios"]:
        assert scenario["unrecovered_gap"] == scenario["gross_customer_credit"] - scenario["potential_provider_credit"]
        for citation in scenario["citations"]:
            source = (bundle / "bundle" / "contracts" / f"{citation['document_key']}.txt").read_text(encoding="utf-8")
            assert citation["quote"] in source
    assert bob.get(route, headers=HEADERS).json()["documents"] == []
