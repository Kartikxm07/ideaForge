-- 006_odin_state.sql: Tables supporting ODIN multi-agent contract intelligence state

CREATE TABLE IF NOT EXISTS odin_workstreams (
  ws_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  run_id TEXT,
  type TEXT NOT NULL CHECK(type IN ('contract', 'cross')),
  doc_ids TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'needs_review', 'done', 'incomplete')),
  reason TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_ws_owner_status ON odin_workstreams(owner_id, status);

CREATE TABLE IF NOT EXISTS odin_documents (
  doc_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  path TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('ok', 'incomplete', 'malformed')),
  parse_warnings TEXT NOT NULL,
  clause_count INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_docs_owner ON odin_documents(owner_id);

CREATE TABLE IF NOT EXISTS odin_clauses (
  clause_id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  section_ref TEXT NOT NULL,
  heading TEXT NOT NULL,
  body TEXT NOT NULL,
  char_offset_start INTEGER,
  char_offset_end INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY(doc_id) REFERENCES odin_documents(doc_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_odin_clauses_doc ON odin_clauses(owner_id, doc_id);

CREATE TABLE IF NOT EXISTS odin_extractions (
  ext_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  run_id TEXT,
  doc_id TEXT NOT NULL,
  field TEXT NOT NULL,
  value TEXT NOT NULL,
  clause_ref TEXT NOT NULL,
  quote TEXT NOT NULL,
  confidence REAL NOT NULL,
  ambiguity_flag INTEGER DEFAULT 0,
  ambiguity_note TEXT,
  source_tag TEXT DEFAULT 'sourced',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_ext_doc_field ON odin_extractions(owner_id, doc_id, field);

CREATE TABLE IF NOT EXISTS odin_effective_terms (
  term_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  term_key TEXT NOT NULL,
  value TEXT NOT NULL,
  derived_from TEXT NOT NULL,
  superseded_by TEXT,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_terms_doc_key ON odin_effective_terms(owner_id, doc_id, term_key);

CREATE TABLE IF NOT EXISTS odin_events (
  event_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  channel TEXT,
  sender TEXT,
  recipient TEXT,
  subject TEXT,
  body TEXT NOT NULL,
  raw_json TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_events_owner_ts ON odin_events(owner_id, timestamp);

CREATE TABLE IF NOT EXISTS odin_event_map (
  map_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  doc_id TEXT,
  clause_ref TEXT,
  relevance TEXT CHECK(relevance IN ('action', 'info', 'noise')),
  reasoning TEXT,
  valid_notice INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY(event_id) REFERENCES odin_events(event_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_odin_event_map_ev ON odin_event_map(owner_id, event_id);

CREATE TABLE IF NOT EXISTS odin_alerts (
  alert_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  clock_t TEXT NOT NULL,
  severity TEXT NOT NULL CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  type TEXT NOT NULL CHECK(type IN ('deadline', 'renewal', 'payment', 'breach', 'other')),
  doc_id TEXT NOT NULL,
  clause_ref TEXT,
  message TEXT NOT NULL,
  due_date TEXT,
  event_ids TEXT,
  acknowledged INTEGER DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_alerts_clock_sev ON odin_alerts(owner_id, clock_t, severity);

CREATE TABLE IF NOT EXISTS odin_timeline (
  timeline_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  clock_t TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  item_type TEXT NOT NULL CHECK(item_type IN ('past', 'due_now', 'upcoming', 'penalty_trigger', 'missed')),
  date TEXT NOT NULL,
  description TEXT NOT NULL,
  amount REAL,
  citation TEXT,
  status TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_timeline_clock_doc ON odin_timeline(owner_id, clock_t, doc_id);

CREATE TABLE IF NOT EXISTS odin_exposure (
  exposure_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  clock_t TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  scenario TEXT NOT NULL CHECK(scenario IN ('expected', 'worst_case')),
  amount REAL NOT NULL,
  breakdown TEXT,
  formula TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_exposure_clock_doc ON odin_exposure(owner_id, clock_t, doc_id);

CREATE TABLE IF NOT EXISTS odin_findings (
  finding_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  clock_t TEXT NOT NULL,
  source_agent TEXT DEFAULT 'loki',
  docs TEXT NOT NULL,
  citations TEXT NOT NULL,
  attack_path TEXT NOT NULL,
  severity TEXT NOT NULL CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  likelihood REAL NOT NULL,
  tag TEXT NOT NULL CHECK(tag IN ('sourced', 'inferred')),
  status TEXT NOT NULL CHECK(status IN ('proposed', 'confirmed', 'challenged', 'noise', 'ruled', 'closed')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_findings_clock_status ON odin_findings(owner_id, clock_t, status);

CREATE TABLE IF NOT EXISTS odin_clarifications (
  req_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  clause_ref TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT,
  round INTEGER DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_clarify_finding ON odin_clarifications(owner_id, finding_id);

CREATE TABLE IF NOT EXISTS odin_verifications (
  verif_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK(verdict IN ('confirmed', 'challenged', 'noise')),
  reasons TEXT NOT NULL,
  event_ids TEXT,
  clause_checks TEXT,
  recomputed_numbers TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_verif_finding ON odin_verifications(owner_id, finding_id);

CREATE TABLE IF NOT EXISTS odin_rulings (
  ruling_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('upheld', 'rejected', 'partial')),
  rationale TEXT NOT NULL,
  citations TEXT NOT NULL,
  round INTEGER DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_rulings_finding ON odin_rulings(owner_id, finding_id);

CREATE TABLE IF NOT EXISTS odin_actions (
  action_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  finding_id TEXT,
  type TEXT NOT NULL CHECK(type IN ('renewal', 'termination', 'breach', 'cure', 'rejection', 'amendment', 'escalation')),
  recipient TEXT NOT NULL,
  recipient_address TEXT NOT NULL,
  signer TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  citations TEXT NOT NULL,
  deadline TEXT NOT NULL,
  confidence REAL NOT NULL,
  needs_human_approval INTEGER DEFAULT 1,
  status TEXT NOT NULL CHECK(status IN ('draft_pending_approval', 'approved', 'rejected')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_actions_owner_status ON odin_actions(owner_id, status);

CREATE TABLE IF NOT EXISTS odin_messages (
  msg_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  from_agent TEXT NOT NULL,
  to_agent TEXT NOT NULL,
  type TEXT NOT NULL,
  payload_ref TEXT,
  clock_t TEXT,
  timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_messages_owner_clock ON odin_messages(owner_id, clock_t);

CREATE TABLE IF NOT EXISTS odin_llm_calls (
  call_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  cached INTEGER DEFAULT 0,
  latency_ms INTEGER DEFAULT 0,
  error TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_llm_hash ON odin_llm_calls(owner_id, prompt_hash);

CREATE TABLE IF NOT EXISTS odin_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  clock_t TEXT NOT NULL,
  summary_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(owner_id, clock_t)
);

CREATE TABLE IF NOT EXISTS odin_reports (
  report_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  content TEXT NOT NULL,
  completeness TEXT NOT NULL CHECK(completeness IN ('COMPLETE', 'INCOMPLETE')),
  reasons TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odin_reports_owner_scope ON odin_reports(owner_id, scope);

CREATE TABLE IF NOT EXISTS odin_parse_errors (
  error_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  source TEXT NOT NULL,
  raw_content TEXT NOT NULL,
  error_message TEXT NOT NULL,
  created_at TEXT NOT NULL
);
