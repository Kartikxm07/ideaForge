CREATE TABLE IF NOT EXISTS web_users (
 id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 password_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS web_orgs (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS web_members (
 user_id TEXT NOT NULL REFERENCES web_users(id), org_id TEXT NOT NULL REFERENCES web_orgs(id),
 role TEXT NOT NULL CHECK(role IN ('admin','reviewer','viewer')), PRIMARY KEY(user_id,org_id)
);
CREATE TABLE IF NOT EXISTS web_sessions (
 digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES web_users(id), org_id TEXT NOT NULL,
 expires_at TEXT NOT NULL, absolute_expiry TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS web_records (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL,
 data TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS web_record_scope ON web_records(owner_id,kind);
CREATE TABLE IF NOT EXISTS web_login_attempts (key TEXT PRIMARY KEY, count INTEGER NOT NULL, reset_at REAL NOT NULL);
