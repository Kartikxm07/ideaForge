CREATE TABLE IF NOT EXISTS document_uploads (
  document_id TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL,
  filename TEXT NOT NULL,
  media_type TEXT NOT NULL,
  raw_sha256 TEXT NOT NULL,
  raw BLOB NOT NULL,
  page_count INTEGER,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_document_upload_owner ON document_uploads(owner_id,document_id);
