CREATE TABLE IF NOT EXISTS operational_events (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  channel TEXT NOT NULL,
  sender TEXT NOT NULL,
  recipient TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  source TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  UNIQUE(owner_id,event_id)
);
CREATE INDEX IF NOT EXISTS idx_operational_events_owner_time ON operational_events(owner_id,occurred_at,event_id);
