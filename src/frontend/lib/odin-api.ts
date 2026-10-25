export async function odinApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

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
