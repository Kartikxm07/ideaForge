"""Local evidence snapshots and Ethereum Sepolia hash anchoring.

Callable by agents; signing is deliberately not exposed on the public Thor API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3

CHAIN_ID = 11155111
PREFIX = b"thor:evidence:v1:sha256:"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def snapshot(db_path: str | Path) -> dict:
    """Read both tables in one SQLite snapshot; omit volatile IDs/timestamps.

    Commits canonical evidence and PDF mappings, not original source files or
    the regenerable embedding matrix. Call after ingestion has completed.
    """
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        chunks = [dict(r) for r in conn.execute("SELECT * FROM odin_chunks")]
        facts = [dict(r) for r in conn.execute("SELECT * FROM thor_facts")]
    if not chunks:
        raise ValueError("No evidence chunks found; finish ingestion first.")
    for row in chunks:
        for key in ("row_id", "created_at"):
            row.pop(key, None)
        for key in ("rects_json", "metadata_json"):
            row[key] = json.loads(row[key])
    for row in facts:
        for key in ("id", "created_at"):
            row.pop(key, None)
    manifest = {"schema": "thor-evidence-v1", "chunks": sorted(chunks, key=canonical_bytes),
                "facts": sorted(facts, key=canonical_bytes)}
    return {"manifest": manifest, "sha256": hashlib.sha256(canonical_bytes(manifest)).hexdigest()}


def payload(bundle: dict) -> bytes:
    digest = hashlib.sha256(canonical_bytes(bundle["manifest"])).hexdigest()
    if digest != bundle["sha256"]:
        raise ValueError("Snapshot digest mismatch: local evidence was modified.")
    return PREFIX + bytes.fromhex(digest)


def save_new(path: str | Path, value: dict):
    """Exclusive creation prevents accidentally overwriting evidence/receipts."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())


def connect(rpc_url: str | None = None):
    from web3 import Web3
    rpc = rpc_url or os.environ.get("THOR_SEPOLIA_RPC_URL")
    if not rpc:
        raise ValueError("Set THOR_SEPOLIA_RPC_URL in the process environment.")
    web3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    if web3.eth.chain_id != CHAIN_ID:
        raise ValueError("Refusing to use a network other than Ethereum Sepolia (11155111).")
    return web3


def submit(bundle: dict, pending_path: str | Path, web3=None, private_key: str | None = None) -> dict:
    """Sign a zero-value self-transfer with the digest as transaction data.

    Persist signed bytes BEFORE broadcasting so ambiguous network failures can
    be recovered by rebroadcasting the identical transaction, never re-signing.
    Serialize submissions from a given wallet (including other applications).
    """
    data = payload(bundle)
    web3 = web3 or connect()
    if web3.eth.chain_id != CHAIN_ID:
        raise ValueError("Only Sepolia is supported.")
    key = private_key or os.environ.get("THOR_TESTNET_PRIVATE_KEY")
    if not key:
        raise ValueError("Set THOR_TESTNET_PRIVATE_KEY in the process environment.")
    account = web3.eth.account.from_key(key)
    tx = {"chainId": CHAIN_ID, "from": account.address, "to": account.address,
          "value": 0, "data": data, "nonce": web3.eth.get_transaction_count(account.address, "pending"),
          "gasPrice": web3.eth.gas_price}
    tx["gas"] = web3.eth.estimate_gas(tx)
    # Hard cost ceiling: at most 0.001 test ETH per anchor.
    if tx["gas"] * tx["gasPrice"] > 10**15:
        raise ValueError("Estimated fee exceeds the 0.001 test ETH ceiling; retry later.")
    if web3.eth.get_balance(account.address) < tx["gas"] * tx["gasPrice"]:
        raise ValueError("Wallet needs Sepolia test ETH for gas.")
    signed = account.sign_transaction(tx)
    record = {"chain_id": CHAIN_ID, "sha256": bundle["sha256"],
              "sender": account.address, "transaction_hash": "0x" + bytes(signed.hash).hex(),
              "raw_transaction": "0x" + bytes(signed.raw_transaction).hex(),
              "status": "signed", "explorer_url": "https://sepolia.etherscan.io/tx/0x" + bytes(signed.hash).hex()}
    save_new(pending_path, record)
    web3.eth.send_raw_transaction(signed.raw_transaction)
    return {**record, "status": "submitted"}


def receipt(bundle: dict, record: dict, web3=None) -> dict:
    """Fetch a mined receipt and verify calldata against the saved manifest.

    A mined transaction is not necessarily finalized. Returned confirmations
    describe the observed head; rerun later to detect reorgs.
    """
    expected = payload(bundle)
    web3 = web3 or connect()
    if web3.eth.chain_id != CHAIN_ID or record["chain_id"] != CHAIN_ID:
        raise ValueError("Only Sepolia is supported.")
    tx_hash = record["transaction_hash"]
    tx = web3.eth.get_transaction(tx_hash)
    mined = web3.eth.get_transaction_receipt(tx_hash)
    if (bytes(tx["input"]) != expected or int(tx["value"]) != 0
            or tx["from"].lower() != record["sender"].lower()
            or (tx["to"] or "").lower() != record["sender"].lower()
            or record["sha256"] != bundle["sha256"]):
        raise ValueError("Transaction does not match this evidence anchor.")
    if mined["status"] != 1:
        raise ValueError("Anchor transaction failed on-chain.")
    block = web3.eth.get_block(mined["blockNumber"])
    if bytes(block["hash"]) != bytes(mined["blockHash"]):
        raise ValueError("Receipt block is no longer canonical; retry.")
    return {"chain_id": CHAIN_ID, "sha256": bundle["sha256"],
            "transaction_hash": tx_hash, "sender": tx["from"], "status": "mined",
            "block_number": mined["blockNumber"], "block_hash": "0x" + bytes(mined["blockHash"]).hex(),
            "block_timestamp": block["timestamp"], "gas_used": mined["gasUsed"],
            "confirmations": web3.eth.block_number - mined["blockNumber"] + 1,
            "evidence_matches": True, "explorer_url": "https://sepolia.etherscan.io/tx/" + tx_hash}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    prepare = subs.add_parser("prepare")
    prepare.add_argument("--db", default=str(Path(__file__).with_name("odin_chunks.db")))
    prepare.add_argument("--out", required=True)
    send = subs.add_parser("submit")
    send.add_argument("--snapshot", required=True)
    send.add_argument("--pending", required=True)
    check = subs.add_parser("receipt")
    check.add_argument("--snapshot", required=True)
    check.add_argument("--pending", required=True)
    check.add_argument("--out", required=True)
    retry = subs.add_parser("rebroadcast")
    retry.add_argument("--pending", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            bundle = snapshot(args.db)
            save_new(args.out, bundle)
            print(json.dumps({"sha256": bundle["sha256"], "snapshot": args.out}))
        elif args.command == "rebroadcast":
            record = json.loads(Path(args.pending).read_text(encoding="utf-8"))
            web3 = connect()
            if record["chain_id"] != CHAIN_ID:
                raise ValueError("Only Sepolia is supported.")
            raw = bytes.fromhex(record["raw_transaction"].removeprefix("0x"))
            if "0x" + bytes(web3.keccak(raw)).hex() != record["transaction_hash"]:
                raise ValueError("Signed transaction was modified.")
            web3.eth.send_raw_transaction(raw)
            print(record["transaction_hash"])
        else:
            bundle = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
            if args.command == "submit":
                result = submit(bundle, args.pending)
                result.pop("raw_transaction", None)
            else:
                record = json.loads(Path(args.pending).read_text(encoding="utf-8"))
                result = receipt(bundle, record)
                save_new(args.out, result)
            print(json.dumps(result, indent=2))
    except Exception as exc:
        # Provider exceptions may contain credential-bearing RPC URLs.
        if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], str):
            parser.exit(1, "Anchor error: " + exc.args[0] + "\n")
        parser.exit(1, f"Anchor operation incomplete ({type(exc).__name__}). "
                    "Keep the pending file; check receipt or rebroadcast before submitting again.\n")


if __name__ == "__main__":
    main()
