export async function odinApi<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("odin_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init?.headers as Record<string, string>) };
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

odinApi.session = () => odinApi<OdinSession>("/auth/session");
odinApi.latestAgentRun = () => odinApi<OdinRun>("/workspace/agents/runs/latest");
odinApi.logout = () => odinApi("/auth/logout", { method: "POST" });


export async function odinUploadFile(file: File): Promise<{ kind: "contract" | "events"; title?: string; created?: number; quarantined?: number; error_lines?: number[] }> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/v1/workspace/upload-file", { method: "POST", body: form, credentials: "same-origin" });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : `Upload failed (${response.status})`);
  return result;
}

export type OdinSession = {
  user: { id: string; name: string; email: string };
  organization_id: string;
  role: string;
  organizations: { id: string; name: string; role: string }[];
};

export type OdinCitation = { document_key: string; clause_ref: string; quote: string; offset?: number };

export type OdinRun = {
  id?: string;
  status: string;
  error?: string | null;
  document_keys?: string[];
  extractions: { id: string; document_key: string; field: string; value: string; confidence: number; ambiguity?: string; citation: OdinCitation }[];
  timeline: { id: string; document_key: string; date: string; description: string; citation: OdinCitation }[];
  scenarios?: { id: string; clock_t: string; kind: string; summary: string; elapsed_timeline_ids: string[]; upheld_ruling_ids: string[]; review_ruling_ids: string[]; exposure_amount: number | null; limitation: string }[];
  findings: { id: string; claim: string; reasoning: string; severity: string; citations: OdinCitation[] }[];
  verifications: { id: string; finding_id: string; verdict: string; reason: string; event_ids: string[] }[];
  rulings: { id: string; finding_id: string; outcome: string; rationale: string; draft_notice?: string | null; citations: OdinCitation[] }[];
  email_drafts?: { id: string; finding_id: string; status: "DRAFT" | "APPROVED" | "SENT"; recipient: string | null; subject: string; body: string; sent_at?: string | null }[];
  messages: { id: string; from: string; to: string; message: string; at: string }[];
};

export type OdinContract = { document_key: string; title: string; status: string; severity: string; next_deadline: string | null; warning?: string | null };
export type OdinGraph = { nodes: { id: string; label: string; kind: string; severity?: string }[]; edges: { id: string; source: string; target: string; label: string }[] };

// ── FR1 - FR8 Official Autonomous Trial Types ───────────────────────────────

export interface CaseFile {
  case_id: string;
  question: string;
  as_of_date: string;
  verified: boolean;
  verification_notes: string;
  run_number: number;
  documents_gathered: { id: string; title: string; length: number }[];
  events_count: number;
  created_at: string;
}

export interface TrialClaim {
  id: string;
  claim: string;
  document_id: string;
  clause_ref: string;
  quote: string;
  country: string;
  sector: string;
  estimate_high?: number;
  estimate_low?: number;
  type: "SOURCED_FACT" | "INFERENCE";
  rationale: string;
}

export interface TrialAttack {
  id: string;
  attacker: "Thor" | "Loki";
  target_claim_id: string;
  attack_point: string;
  new_evidence?: {
    document_id: string;
    clause_ref: string;
    quote: string;
  };
}

export interface TrialDefence {
  id: string;
  defender: "Thor" | "Loki";
  target_claim_id: string;
  response_type: "DEFEND" | "CONCEDE";
  argument: string;
}

export interface OdinRuling {
  id: string;
  claim_id: string;
  agent: "Thor" | "Loki";
  topic: string;
  country: string;
  sector: string;
  fact_type: "SOURCED_FACT" | "INFERENCE";
  classification: "ESTABLISHED" | "CONTESTED" | "CONCEDED";
  rationale: string;
  established_exposure: number;
  low_bound: number;
  high_bound: number;
}

export interface SufficiencyCheck {
  is_sufficient: boolean;
  run_number: number;
  decision: "PROCEED_TO_BRIEFING" | "SEND_BACK_FOR_RUN_2";
  missing_evidence: string[];
  message: string;
}

export interface TrialRun {
  run_number: number;
  round1: {
    thor_claims: TrialClaim[];
    loki_claims: TrialClaim[];
  };
  round2: {
    attacks: TrialAttack[];
    defences: TrialDefence[];
  };
  odin_rulings: OdinRuling[];
  sufficiency: SufficiencyCheck;
}

export interface ExposureRow {
  topic: string;
  country: string;
  sector: string;
  low_estimate: number;
  high_estimate: number;
  established_amount: number;
  status: "ESTABLISHED" | "CONTESTED" | "CONCEDED";
  fact_type: "SOURCED_FACT" | "INFERENCE";
  lead_claim: string;
  rationale: string;
}

export interface FinalBriefing {
  title: string;
  case_id: string;
  as_of_date: string;
  executive_summary: string;
  established_findings: OdinRuling[];
  contested_findings: OdinRuling[];
  conceded_findings: OdinRuling[];
  exposure_summary: {
    total_low: number;
    total_high: number;
    total_established: number;
    net_gap: number;
  };
  next_quarter_outlook: string;
  assumptions: string[];
  citations: {
    id?: string;
    document_id: string;
    title: string;
    timestamp: string;
    clause_ref: string;
    quote: string;
  }[];
  sources_consulted: string[];
  adjudicated_at: string;
}

export interface WorldFeedItem {
  id: string;
  timestamp: string;
  source: string;
  headline: string;
  body: string;
  related_doc_id?: string;
  type: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
}

export interface TrialResult {
  status: "COMPLETED" | "ABORTED";
  reason?: string;
  case_file: CaseFile;
  runs: TrialRun[];
  final_briefing: FinalBriefing | null;
  exposure_table: ExposureRow[];
  news_feed: WorldFeedItem[];
  agent_memories: {
    heimdall: string[];
    thor: string[];
    loki: string[];
    odin: string[];
  };
  as_of_date: string;
  timestamp: string;
}

// ── Trial API Client Helpers ────────────────────────────────────────────────

export const trialApi = {
  getLatest: () => odinApi<TrialResult>("/workspace/trial/latest"),
  runTrial: (question: string, asOfDate: string) =>
    odinApi<TrialResult>("/workspace/trial/run", {
      method: "POST",
      body: JSON.stringify({ question, as_of_date: asOfDate }),
    }),
  getWorldFeed: () => odinApi<WorldFeedItem[]>("/workspace/world/feed"),
  getWorldDoc: (docKey: string) =>
    odinApi<{ document_key: string; title: string; content: string; content_sha256?: string }>(
      `/workspace/world/doc/${encodeURIComponent(docKey)}`
    ),
};
