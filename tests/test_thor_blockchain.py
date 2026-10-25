import copy
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from thor_agent.blockchain import CHAIN_ID, payload, receipt, save_new, snapshot, submit


@pytest.fixture
def evidence(tmp_path):
    db = tmp_path / "evidence.db"
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE odin_chunks (row_id INTEGER, chunk_id TEXT, text TEXT,
                rects_json TEXT, metadata_json TEXT, created_at TEXT);
            CREATE TABLE thor_facts (id INTEGER, quote TEXT, created_at TEXT);
            INSERT INTO odin_chunks VALUES (1, 'B1:1', 'Exact evidence', '[]', '{"b":2,"a":1}', 'today');
            INSERT INTO thor_facts VALUES (1, 'Exact evidence', 'today');
        """)
    return db


def test_stable_and_content_sensitive(evidence):
    original = snapshot(evidence)
    with sqlite3.connect(evidence) as conn:
        conn.execute("UPDATE odin_chunks SET row_id=99, created_at='tomorrow', metadata_json=?",
                     ('{"a": 1, "b": 2}',))
        conn.execute("UPDATE thor_facts SET id=99, created_at='tomorrow'")
    assert snapshot(evidence) == original
    with sqlite3.connect(evidence) as conn:
        conn.execute("UPDATE thor_facts SET quote='Changed evidence'")
    assert snapshot(evidence)["sha256"] != original["sha256"]


def test_tamper_and_overwrite_rejected(evidence, tmp_path):
    bundle = snapshot(evidence)
    bundle["manifest"]["facts"][0]["quote"] = "fake"
    with pytest.raises(ValueError, match="mismatch"):
        payload(bundle)
    path = tmp_path / "proof.json"
    save_new(path, {"original": True})
    with pytest.raises(FileExistsError):
        save_new(path, {})


def test_empty_snapshot(evidence):
    with sqlite3.connect(evidence) as conn:
        conn.execute("DELETE FROM odin_chunks")
    with pytest.raises(ValueError, match="No evidence"):
        snapshot(evidence)


def test_mainnet_rejected_before_signing(evidence, tmp_path):
    web3 = SimpleNamespace(eth=SimpleNamespace(chain_id=1))
    with pytest.raises(ValueError, match="Sepolia"):
        submit(snapshot(evidence), tmp_path / "pending.json", web3)


def test_pending_saved_before_failed_broadcast(evidence, tmp_path, monkeypatch):
    monkeypatch.setenv("THOR_TESTNET_PRIVATE_KEY", "mock-key")
    account = Mock(address="0xabc")
    account.sign_transaction.return_value = SimpleNamespace(hash=b"h" * 32, raw_transaction=b"signed")
    eth = Mock(chain_id=CHAIN_ID, gas_price=1)
    eth.account.from_key.return_value = account
    eth.get_transaction_count.return_value = 0
    eth.estimate_gas.return_value = 22000
    eth.get_balance.return_value = 10**18
    pending = tmp_path / "pending.json"

    def fail_broadcast(raw):
        assert pending.exists()
        assert raw == b"signed"
        raise TimeoutError()

    eth.send_raw_transaction.side_effect = fail_broadcast
    with pytest.raises(TimeoutError):
        submit(snapshot(evidence), pending, SimpleNamespace(eth=eth))
    assert "mock-key" not in pending.read_text()


def test_receipt_matches_and_rejects_wrong_payload_or_failed_tx(evidence):
    bundle = snapshot(evidence)
    record = {"chain_id": CHAIN_ID, "transaction_hash": "0x123", "sender": "0xabc",
              "sha256": bundle["sha256"]}
    tx = {"input": payload(bundle), "value": 0, "from": "0xabc", "to": "0xabc"}
    mined = {"status": 1, "blockNumber": 100, "blockHash": b"block", "gasUsed": 22000}
    eth = Mock(chain_id=CHAIN_ID, block_number=102)
    eth.get_transaction.return_value = tx
    eth.get_transaction_receipt.return_value = mined
    eth.get_block.return_value = {"hash": b"block", "timestamp": 12345}
    web3 = SimpleNamespace(eth=eth)
    result = receipt(bundle, record, web3)
    assert result["evidence_matches"] and result["confirmations"] == 3
    eth.get_transaction.return_value = {**tx, "input": b"wrong"}
    with pytest.raises(ValueError, match="does not match"):
        receipt(bundle, record, web3)
    eth.get_transaction.return_value = tx
    eth.get_transaction_receipt.return_value = {**mined, "status": 0}
    with pytest.raises(ValueError, match="failed"):
        receipt(bundle, record, web3)
    eth.get_transaction_receipt.return_value = mined
    eth.get_block.return_value = {"hash": b"reorg", "timestamp": 12345}
    with pytest.raises(ValueError, match="canonical"):
        receipt(bundle, record, web3)
