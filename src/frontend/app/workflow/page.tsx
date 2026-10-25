"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { odinApi, type OdinRun, type OdinSession } from "@/lib/odin-api";
import {
  ArrowDown, CheckCircle2, CircleDot, Clock3, FileQuestion,
  Loader2, LogOut, MessageSquare, RefreshCw, Send,
  ShieldCheck, Swords, ThumbsDown, ThumbsUp, TriangleAlert, UserCheck, Zap,
  Scale, Layers,
} from "lucide-react";
import { TrialView } from "@/components/views/TrialView";

/* ── types ─────────────────────────────────────────────────────────────── */
type StepStatus = "idle" | "running" | "done" | "error";
interface PipelineStep { id: string; name: string; role: string; icon: React.ElementType; color: string; glow: string; }
interface Citation { document_key: string; clause_ref: string; quote: string; }
interface ReviewQuestion {
  id: string; run_id: string; outcome: string; finding_claim: string;
  rationale: string; draft_notice: string | null; citations: Citation[];
  question: string; answered: boolean; answer: string | null;
  decision: string | null; answered_at: string | null;
}
interface ReviewData { run_id: string; status: string; questions: ReviewQuestion[]; pending: number; }

/* ── pipeline config ────────────────────────────────────────────────────── */
const PIPELINE: PipelineStep[] = [
  { id: "odin",     name: "ODIN",     role: "Orchestrator — ingests contracts, dispatches all agents",      icon: Zap,         color: "#d4a017", glow: "rgba(212,160,23,0.35)" },
  { id: "thor",     name: "Thor",     role: "Extractor — finds every obligation, date & clause with quotes", icon: FileQuestion, color: "#3a75b0", glow: "rgba(58,117,176,0.35)" },
  { id: "loki",     name: "Loki",     role: "Devil's Advocate — surfaces adversarial flaws & risks",         icon: Swords,       color: "#c94d56", glow: "rgba(201,77,86,0.35)"  },
  { id: "heimdall", name: "Heimdall", role: "Verifier — checks every Loki claim against operational events", icon: ShieldCheck,  color: "#1e7a5c", glow: "rgba(30,122,92,0.35)"  },
  { id: "tyr",      name: "Tyr",      role: "Arbiter — rules upheld/rejected, drafts notices for humans",    icon: UserCheck,    color: "#7c4db8", glow: "rgba(124,77,184,0.35)" },
  { id: "norns",    name: "Norns",    role: "Forecasters — worst-case scenario & timeline projections",       icon: Clock3,       color: "#b87340", glow: "rgba(184,115,64,0.35)" },
];

/* ── derive per-agent status from live run ─────────────────────────────── */
function deriveStatuses(run: OdinRun | null): Record<string, StepStatus> {
  if (!run || run.status === "NOT_RUN") return {};
  const s = run.status;
  const done = s === "COMPLETE" || s === "INCOMPLETE";
  const hasE = run.extractions.length > 0;
  const hasF = run.findings.length > 0;
  const hasV = run.verifications.length > 0;
  const hasR = run.rulings.length > 0;
  const hasT = run.timeline.length > 0;
  return {
    odin:     done || s === "RUNNING" ? "done" : "running",
    thor:     hasE ? "done" : s === "RUNNING" ? "running" : "idle",
    loki:     hasF ? "done" : (hasE && s === "RUNNING") ? "running" : "idle",
    heimdall: hasV ? "done" : (hasF && s === "RUNNING") ? "running" : "idle",
    tyr:      hasR ? "done" : (hasV && s === "RUNNING") ? "running" : "idle",
    norns:    done && hasT ? "done" : done ? "idle" : (hasR && s === "RUNNING") ? "running" : "idle",
  };
}

/* ── tiny shared bits ───────────────────────────────────────────────────── */
function StatusDot({ status }: { status: StepStatus }) {
  if (status === "done")    return <CheckCircle2 className="text-emerald-400" size={16} />;
  if (status === "running") return <Loader2 className="animate-spin text-yellow-400" size={16} />;
  if (status === "error")   return <TriangleAlert className="text-red-400" size={16} />;
  return <CircleDot className="text-slate-600" size={16} />;
}
function Pill({ text, color }: { text: string; color: string }) {
  return (
    <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white" style={{ background: color }}>
      {text}
    </span>
  );
}

/* ── main page ──────────────────────────────────────────────────────────── */
export default function WorkflowPage() {
  const router = useRouter();
  const [session, setSession] = useState<OdinSession | null>(null);
  const [run, setRun] = useState<OdinRun | null>(null);
  const [review, setReview] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modal, setModal] = useState<ReviewQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [decision, setDecision] = useState<"Approve"|"Reject"|"Escalate">("Approve");
  const [submitting, setSubmitting] = useState(false);
  const [activeWorkflowTab, setActiveWorkflowTab] = useState<"pipeline" | "trial" | "review">("trial");
  const [toast, setToast] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchAll = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true); else setRefreshing(true);
    try {
      const [sess, latest] = await Promise.all([odinApi.session(), odinApi.latestAgentRun()]);
      setSession(sess); setRun(latest);
      if (latest?.id && latest.status !== "NOT_RUN") {
        const token = typeof window !== "undefined" ? localStorage.getItem("odin_token") || "" : "";
        const rd = await fetch(`/api/v1/workspace/agents/runs/${latest.id}/review-questions`,
          { headers: { Authorization: `Bearer ${token}` } });
        if (rd.ok) setReview(await rd.json());
      }
    } catch { router.replace("/login"); }
    finally { setLoading(false); setRefreshing(false); }
  }, [router]);

  useEffect(() => { fetchAll(); }, [fetchAll]);
  useEffect(() => {
    if (run?.status === "RUNNING") pollRef.current = setTimeout(() => fetchAll(true), 6000);
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, [run, fetchAll]);

  const statuses = deriveStatuses(run);

  async function submitAnswer() {
    if (!modal || !run?.id || !answer.trim()) return;
    setSubmitting(true);
    try {
      const token = localStorage.getItem("odin_token") || "";
      const res = await fetch(`/api/v1/workspace/agents/runs/${run.id}/review-questions/${modal.id}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ answer: answer.trim(), decision }),
      });
      if (res.ok) {
        setToast(`Decision "${decision}" recorded`);
        setModal(null); setAnswer("");
        await fetchAll(true);
        setTimeout(() => setToast(null), 4000);
      }
    } finally { setSubmitting(false); }
  }

  if (loading) return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a1628]">
      <Loader2 className="animate-spin text-[#3a75b0]" size={40} />
    </div>
  );

  const pending = review?.pending ?? 0;

  return (
    <div className="min-h-screen bg-[#0a1628] font-sans text-white">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-white/10 bg-[#0a1628]/90 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#17375b]">
            <Zap size={17} className="text-[#d4a017]" />
          </div>
          <span className="text-base font-bold tracking-tight">ODIN · Agent Workflow</span>
        </div>
        <div className="flex items-center gap-2">
          {pending > 0 && (
            <span className="rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold">
              {pending} pending
            </span>
          )}
          <button onClick={() => fetchAll(true)}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/5">
            <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} /> Refresh
          </button>
          <button onClick={() => router.push("/war-room")}
            className="rounded-lg bg-[#17375b] px-3 py-1.5 text-xs font-semibold hover:bg-[#1f4a7a]">
            War Room →
          </button>
          <button onClick={async () => { await odinApi.logout(); router.replace("/login"); }}
            className="text-slate-500 hover:text-white"><LogOut size={17} /></button>
        </div>
      </header>

      {/* ── Workflow Sub-Header Tabs ──────────────────────────────────── */}
      <div className="border-b border-white/10 bg-[#0d1c33] px-6 py-2.5">
        <div className="mx-auto flex max-w-5xl items-center gap-2">
          <button
            onClick={() => setActiveWorkflowTab("trial")}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
              activeWorkflowTab === "trial"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/25"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Swords size={14} />
            <span>Trial Chamber (FR7.2)</span>
          </button>
          <button
            onClick={() => setActiveWorkflowTab("pipeline")}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
              activeWorkflowTab === "pipeline"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/25"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Zap size={14} />
            <span>Agent Pipeline Flow (FR5.1)</span>
          </button>
          <button
            onClick={() => setActiveWorkflowTab("review")}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
              activeWorkflowTab === "review"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/25"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <UserCheck size={14} />
            <span>Human Review Q&A</span>
            {pending > 0 && (
              <span className="rounded-full bg-red-500 px-1.5 py-0.2 text-[10px] font-bold text-white">
                {pending}
              </span>
            )}
          </button>
        </div>
      </div>

      <div className="mx-auto max-w-5xl space-y-12 px-4 py-10">
        {activeWorkflowTab === "trial" && <TrialView />}

        {activeWorkflowTab === "pipeline" && (
          <section>
            <h2 className="mb-6 text-xl font-bold">Agent Pipeline</h2>

          <div className="flex flex-col items-center">
            {PIPELINE.map((step, i) => {
              const st = statuses[step.id] ?? "idle";
              const Icon = step.icon;
              return (
                <div key={step.id} className="flex w-full max-w-2xl flex-col items-center">
                  {/* card */}
                  <div className="flex w-full items-center gap-4 rounded-2xl border px-5 py-4 transition-all duration-300"
                    style={{
                      borderColor: st === "idle" ? "rgba(255,255,255,0.07)" : step.color,
                      background: st === "running"
                        ? `linear-gradient(135deg,rgba(10,22,40,0.97),rgba(10,22,40,0.85))`
                        : "rgba(255,255,255,0.04)",
                      boxShadow: st === "running" ? `0 0 28px ${step.glow}` : "none",
                    }}>
                    {/* icon */}
                    <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl"
                      style={{ background: `${step.color}18`, border: `1.5px solid ${step.color}55` }}>
                      <Icon size={22} style={{ color: step.color }} />
                    </div>
                    {/* text */}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold" style={{ color: step.color }}>{step.name}</span>
                        {st === "running" && (
                          <span className="animate-pulse rounded-full bg-yellow-400/15 px-2 py-0.5 text-[10px] font-bold text-yellow-300 uppercase">
                            Running
                          </span>
                        )}
                        {st === "done" && (
                          <span className="rounded-full bg-emerald-400/15 px-2 py-0.5 text-[10px] font-bold text-emerald-400 uppercase">
                            Done
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-slate-400">{step.role}</p>
                      {/* output stats */}
                      {run && st === "done" && (
                        <div className="mt-1.5 flex flex-wrap gap-3 text-[11px]">
                          {step.id === "thor"     && <span className="text-slate-400">{run.extractions.length} extracted terms</span>}
                          {step.id === "loki"     && <span className="text-slate-400">{run.findings.length} proposed risks</span>}
                          {step.id === "heimdall" && <>
                            <span className="text-emerald-400">{(run.verifications as any[]).filter(v => v.verdict === "confirmed").length} confirmed</span>
                            <span className="text-yellow-400">{(run.verifications as any[]).filter(v => v.verdict === "challenged").length} challenged</span>
                          </>}
                          {step.id === "tyr"  && <>
                            <span className="text-emerald-400">{(run.rulings as any[]).filter(r => r.outcome === "upheld").length} upheld</span>
                            <span className="text-amber-400">{(run.rulings as any[]).filter(r => r.outcome === "needs_review").length} needs review</span>
                          </>}
                          {step.id === "norns" && <span className="text-slate-400">{run.timeline.length} timeline events</span>}
                        </div>
                      )}
                    </div>
                    <StatusDot status={st} />
                  </div>

                  {/* connector */}
                  {i < PIPELINE.length - 1 && (
                    <div className="flex flex-col items-center py-0.5">
                      <div className="h-5 w-px bg-white/10" />
                      <ArrowDown size={13} className="text-slate-700" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* run status chip */}
          <div className="mt-6 flex justify-center">
            {!run || run.status === "NOT_RUN" ? (
              <p className="rounded-xl border border-white/10 bg-white/5 px-6 py-3 text-sm text-slate-400">
                No agent run yet — upload a contract and start a run from the War Room.
              </p>
            ) : (
              <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-6 py-3">
                <span className="text-sm text-slate-400">Run status:</span>
                <span className="font-bold uppercase tracking-wide text-sm"
                  style={{ color: run.status === "COMPLETE" ? "#34d399" : run.status === "RUNNING" ? "#fbbf24" : run.status === "INCOMPLETE" ? "#f87171" : "#94a3b8" }}>
                  {run.status}
                </span>
              </div>
            )}
          </div>
        </section>
        )}

        {/* ── Human Review ─────────────────────────────────────────────── */}
        {activeWorkflowTab === "review" && review && review.questions.length > 0 && (
          <section>
            <div className="mb-6">
              <h2 className="flex items-center gap-2 text-xl font-bold">
                <MessageSquare size={20} className="text-[#7c4db8]" />
                Human Review
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                Tyr flagged {review.questions.length} finding{review.questions.length !== 1 ? "s" : ""} for your input.
                {pending > 0 && <span className="ml-1 font-semibold text-amber-400">{pending} pending.</span>}
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {review.questions.map(q => (
                <button key={q.id}
                  onClick={() => { setModal(q); setAnswer(q.answer ?? ""); setDecision((q.decision as any) ?? "Approve"); }}
                  className={`rounded-2xl border p-4 text-left transition-all hover:scale-[1.01] ${
                    q.answered ? "border-emerald-500/25 bg-emerald-500/5" : "border-amber-500/35 bg-amber-500/5"}`}>
                  <div className="flex items-start gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="line-clamp-2 text-sm font-semibold text-slate-100">{q.finding_claim}</p>
                      <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{q.rationale}</p>
                    </div>
                    {q.answered
                      ? <CheckCircle2 size={17} className="mt-0.5 flex-shrink-0 text-emerald-400" />
                      : <TriangleAlert size={17} className="mt-0.5 flex-shrink-0 text-amber-400" />}
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Pill text={q.outcome === "upheld" ? "Upheld" : "Needs Review"}
                      color={q.outcome === "upheld" ? "#1e7a5c" : "#7c4db8"} />
                    {q.answered && q.decision && (
                      <Pill text={q.decision}
                        color={q.decision === "Approve" ? "#1e7a5c" : q.decision === "Reject" ? "#c94d56" : "#b87340"} />
                    )}
                    <span className="ml-auto text-[10px] text-slate-500">{q.citations.length} citation{q.citations.length !== 1 ? "s" : ""}</span>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* empty state */}
        {activeWorkflowTab === "review" && (!review || review.questions.length === 0) && (
          <section className="rounded-2xl border border-dashed border-white/10 p-12 text-center">
            <MessageSquare size={36} className="mx-auto text-slate-700" />
            <p className="mt-4 font-semibold text-slate-400">No findings pending human review</p>
            <p className="mt-1 text-sm text-slate-600">Review questions appear once Tyr flags a risk as needing interpretation.</p>
          </section>
        )}
      </div>

      {/* ── Review Modal ─────────────────────────────────────────────────── */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-4 backdrop-blur-sm sm:items-center">
          <div className="flex max-h-[92vh] w-full max-w-2xl flex-col rounded-2xl border border-white/10 bg-[#0f1e31] shadow-2xl">
            {/* head */}
            <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
              <div className="flex items-center gap-2">
                <UserCheck size={18} className="text-[#7c4db8]" />
                <span className="font-bold">Human Review</span>
              </div>
              <button onClick={() => setModal(null)} className="text-slate-500 hover:text-white text-2xl leading-none">×</button>
            </div>

            {/* body */}
            <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
              {/* finding */}
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-[#7c4db8]">Finding</p>
                <p className="text-sm font-semibold text-slate-100">{modal.finding_claim}</p>
              </div>
              {/* rationale */}
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">Tyr&apos;s Rationale</p>
                <p className="text-sm leading-relaxed text-slate-300">{modal.rationale}</p>
              </div>
              {/* draft notice */}
              {modal.draft_notice && (
                <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Draft Notice</p>
                  <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-300">{modal.draft_notice}</p>
                </div>
              )}
              {/* citations */}
              {modal.citations.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Source Citations</p>
                  <div className="space-y-2">
                    {modal.citations.map((c, i) => (
                      <details key={i} className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs">
                        <summary className="cursor-pointer font-semibold text-[#3a75b0]">{c.document_key} · {c.clause_ref}</summary>
                        <blockquote className="mt-2 border-l-2 border-[#d4a017] pl-3 italic text-slate-400">"{c.quote}"</blockquote>
                      </details>
                    ))}
                  </div>
                </div>
              )}
              {/* question box */}
              <div className="rounded-xl border border-[#7c4db8]/40 bg-[#7c4db8]/10 p-4">
                <p className="mb-2 text-xs font-bold uppercase tracking-wider text-[#7c4db8]">⚖ Tyr asks:</p>
                <p className="text-sm leading-relaxed text-slate-200">{modal.question}</p>
              </div>
              {/* decision */}
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Your Decision</p>
                <div className="flex gap-2">
                  {(["Approve","Reject","Escalate"] as const).map(d => (
                    <button key={d} onClick={() => setDecision(d)}
                      className={`flex flex-1 flex-col items-center gap-1 rounded-xl border py-2.5 text-xs font-bold transition-all ${
                        decision === d
                          ? d === "Approve" ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                          : d === "Reject"  ? "border-red-500 bg-red-500/20 text-red-300"
                          :                   "border-amber-500 bg-amber-500/20 text-amber-300"
                          : "border-white/10 bg-white/5 text-slate-400 hover:bg-white/10"}`}>
                      {d === "Approve" ? <ThumbsUp size={13}/> : d === "Reject" ? <ThumbsDown size={13}/> : <TriangleAlert size={13}/>}
                      {d}
                    </button>
                  ))}
                </div>
              </div>
              {/* reasoning */}
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">Your Reasoning</label>
                <textarea value={answer} onChange={e => setAnswer(e.target.value)} rows={4}
                  placeholder="Explain your decision or add context for the record…"
                  className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:border-[#7c4db8] focus:outline-none" />
              </div>
              {/* prior answer */}
              {modal.answered && modal.answer && (
                <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/5 p-3">
                  <p className="mb-1 text-xs font-semibold text-emerald-400">Previously answered:</p>
                  <p className="text-xs text-slate-300">{modal.answer}</p>
                </div>
              )}
            </div>

            {/* footer */}
            <div className="flex items-center gap-3 border-t border-white/10 px-6 py-4">
              <button onClick={() => setModal(null)}
                className="flex-1 rounded-xl border border-white/10 py-2.5 text-sm text-slate-400 hover:bg-white/5">
                Cancel
              </button>
              <button onClick={submitAnswer} disabled={submitting || !answer.trim()}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-[#7c4db8] py-2.5 text-sm font-bold transition-all hover:bg-[#9261d4] disabled:opacity-40">
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                Submit Decision
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Toast ──────────────────────────────────────────────────────── */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold shadow-lg">
          <CheckCircle2 size={15} /> {toast}
        </div>
      )}
    </div>
  );
}
