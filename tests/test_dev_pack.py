from pathlib import Path

from ragnarok.dev_pack import import_dev_pack
from ragnarok.store import Store


def test_supplied_bundle_imports_without_pdf_duplicates(tmp_path):
    root = Path(__file__).resolve().parents[1]
    pack = root / "dataset" / "Pack" / "odin_dev_pack"
    store = Store(tmp_path / "dev-pack.sqlite3")
    store.migrate()
    report = import_dev_pack(store, "demo", pack)
    assert report["document_keys"] == ["A1", "A2", "A3", "B1", "B2", "C1", "D1", "STD"]
    assert report["checkpoints"] == ["2027-03-15", "2027-06-01", "2027-09-15"]
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM documents WHERE owner_id='demo'").fetchone()[0] == 8
        assert db.execute("SELECT count(*) FROM operational_events WHERE owner_id='demo'").fetchone()[0] == 18
        assert db.execute("SELECT count(*) FROM web_records WHERE owner_id='demo' AND kind='agent-context'").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM web_records WHERE owner_id='demo' AND kind='agent-ledger-row'").fetchone()[0] == report["ledger_rows"]
        assert db.execute("SELECT count(*) FROM web_records WHERE owner_id='demo' AND kind='agent-holiday'").fetchone()[0] == report["holiday_rows"]
