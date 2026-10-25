CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  document_key TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (owner_id, document_key)
);
CREATE INDEX IF NOT EXISTS idx_documents_owner_key ON documents(owner_id, document_key);
