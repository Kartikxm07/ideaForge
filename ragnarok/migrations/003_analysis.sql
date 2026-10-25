CREATE TABLE IF NOT EXISTS analysis_runs (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  question TEXT NOT NULL,
  focus TEXT NOT NULL,
  document_keys_json TEXT NOT NULL,
  document_hashes_json TEXT NOT NULL,
  provider_kind TEXT NOT NULL,
  idempotency_key TEXT,
  status TEXT NOT NULL,
  error TEXT,
  rejected_count INTEGER NOT NULL DEFAULT 0,
  lease_until TEXT,
  claim_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(owner_id,idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_analysis_owner_status ON analysis_runs(owner_id,status,created_at);

CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL,
  claim TEXT NOT NULL,
  explanation TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(run_id,ordinal)
);
CREATE INDEX IF NOT EXISTS idx_findings_owner_run ON findings(owner_id,run_id);
