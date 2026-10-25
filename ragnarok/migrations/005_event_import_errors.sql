CREATE TABLE IF NOT EXISTS event_import_errors (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  source_file TEXT NOT NULL,
  line_number INTEGER NOT NULL,
  line_sha256 TEXT NOT NULL,
  error_type TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  UNIQUE(owner_id,source_file,line_number,line_sha256)
);
CREATE INDEX IF NOT EXISTS idx_event_errors_owner_file ON event_import_errors(owner_id,source_file,line_number);
