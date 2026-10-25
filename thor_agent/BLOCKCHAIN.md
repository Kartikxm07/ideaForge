# Thor evidence anchoring (Ethereum Sepolia)

Run after Thor ingestion completes. The snapshot covers canonical chunks,
PDF mappings, metadata and stored facts in one SQLite read transaction. Row IDs
and timestamps are omitted so equivalent evidence has the same SHA-256 digest.
It does not cover original PDF/file bytes or the NumPy embedding matrix.

Only a versioned prefix and 32-byte digest go on-chain, in a zero-value transfer
to the signing wallet itself. No smart contract deployment is required. This
proves that a digest was included in a block; it does not prove that extracted
facts are true. Keep the local snapshot to reproduce the proof.

```powershell
python -m pip install -r thor_agent/requirements-blockchain.txt
python -m thor_agent.blockchain prepare --out data/anchors/run1.snapshot.json
```

Set `THOR_SEPOLIA_RPC_URL` and `THOR_TESTNET_PRIVATE_KEY` in the launching
process environment using a dedicated test wallet funded with Sepolia test ETH.
The module does not automatically load `.env`. Never put the private key in
source code, CLI arguments, or chat. Mainnet and other chain IDs are rejected.

```powershell
python -m thor_agent.blockchain submit --snapshot data/anchors/run1.snapshot.json --pending data/anchors/run1.pending.json
# After the transaction is mined (retry this command if still pending):
python -m thor_agent.blockchain receipt --snapshot data/anchors/run1.snapshot.json --pending data/anchors/run1.pending.json --out data/anchors/run1.receipt.json
```

Receipt output contains the transaction hash, explorer URL, block number/hash,
gas used, confirmation count, and evidence-match result. `mined` does not mean
finalized; repeat receipt retrieval into a new output file later to check again.
The agent can import `snapshot`, `submit`, and `receipt` from
`thor_agent.blockchain` to perform the same workflow programmatically.
Signing is intentionally a local script operation, not an unauthenticated HTTP
endpoint. Serialize all submissions from this wallet to avoid nonce collisions.

A signed transaction is saved before broadcast. If submission times out, do not
submit again: first retrieve its receipt, or resend exactly the saved bytes:

```powershell
python -m thor_agent.blockchain rebroadcast --pending data/anchors/run1.pending.json
```

An already-known transaction response is harmless; check its receipt. Output
files use exclusive creation and are never overwritten. Use a new run name for
new evidence and keep artifacts under ignored `data/anchors/`. The pending file
includes signed transaction bytes, but never the private key. No live receipt is
fabricated when RPC access or a funded wallet is unavailable.

References: [Ethereum networks](https://ethereum.org/developers/docs/networks/),
[Web3.py transactions](https://web3py.readthedocs.io/en/v7.6.0/transactions.html).
