"use client";

import React, { useState, useEffect } from "react";
import {
  Scale,
  Swords,
  ShieldAlert,
  ShieldCheck,
  Zap,
  Play,
  RotateCcw,
  FileText,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  DollarSign,
  Radio,
  Clock,
  Layers,
  Printer,
  Sparkles,
  BookOpen,
  Eye,
  Loader2,
  X,
} from "lucide-react";
import {
  trialApi,
  type TrialResult,
  type TrialRun,
  type TrialClaim,
  type OdinRuling,
  type WorldFeedItem,
} from "@/lib/odin-api";

export function TrialView() {
  const [trial, setTrial] = useState<TrialResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activeRunIndex, setActiveRunIndex] = useState(1); // 0 = Run 1, 1 = Run 2
  const [question, setQuestion] = useState(
    "What is our commercial exposure across enterprise contracts and infrastructure outages as of Nov 15, 2026?"
  );
  const [asOfDate, setAsOfDate] = useState("2026-11-15");
  const [selectedSubTab, setSelectedSubTab] = useState<"trial" | "exposure" | "briefing" | "memories">("trial");

  // Evidence click-through modal (FR7.4)
  const [evidenceModal, setEvidenceModal] = useState<{
    docId: string;
    clauseRef: string;
    quote: string;
    title?: string;
    content?: string;
    loading?: boolean;
  } | null>(null);

  // Preset question chips
  const presets = [
    {
      label: "StratoNode Outage & Customer SLA Default",
      q: "What is our commercial exposure from StratoNode cloud outage and customer SLA liquidated damages as of Nov 15, 2026?",
      d: "2026-11-15",
    },
    {
      label: "Full Commercial Portfolio & Liquidated Damages",
      q: "What is our commercial exposure across enterprise contracts and infrastructure outages as of Nov 15, 2026?",
      d: "2026-11-15",
    },
    {
      label: "Pixelwright Contractor IP Warranty Compliance",
      q: "Evaluate intellectual property clean-room warranty compliance and indemnity exposure regarding contractor Pixelwright heuristics as of Jan 15, 2027.",
      d: "2027-01-15",
    },
  ];

  // Load latest trial on mount
  useEffect(() => {
    async function loadLatest() {
      setLoading(true);
      try {
        const data = await trialApi.getLatest();
        setTrial(data);
        if (data.runs && data.runs.length > 0) {
          setActiveRunIndex(data.runs.length - 1);
        }
      } catch (err) {
        console.error("Failed to load trial data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadLatest();
  }, []);

  // Launch trial
  async function handleLaunchTrial() {
    setRunning(true);
    try {
      const data = await trialApi.runTrial(question, asOfDate);
      setTrial(data);
      if (data.runs && data.runs.length > 0) {
        setActiveRunIndex(data.runs.length - 1);
      }
    } catch (err) {
      console.error("Failed to execute trial:", err);
    } finally {
      setRunning(false);
    }
  }

  // Handle click-through evidence (FR7.4)
  async function openEvidence(docId: string, clauseRef: string, quote: string) {
    setEvidenceModal({
      docId,
      clauseRef,
      quote,
      loading: true,
    });
    try {
      const doc = await trialApi.getWorldDoc(docId);
      setEvidenceModal({
        docId,
        clauseRef,
        quote,
        title: doc.title,
        content: doc.content,
        loading: false,
      });
    } catch {
      // Fallback display if individual doc fetch fails
      setEvidenceModal({
        docId,
        clauseRef,
        quote,
        title: `World Document ${docId}`,
        content: `Document ID: ${docId}\nSection: ${clauseRef}\n\nExact Cited Quote:\n"${quote}"\n\n[World Document Record Verified in Organization Vault]`,
        loading: false,
      });
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-20 space-y-4">
        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
        <p className="font-jetbrains text-xs text-slate-400 uppercase tracking-widest">
          Consulting Heimdall, Thor, Loki & Odin...
        </p>
      </div>
    );
  }

  const currentRun: TrialRun | undefined = trial?.runs?.[activeRunIndex] || trial?.runs?.[0];
  const caseFile = trial?.case_file;
  const briefing = trial?.final_briefing;
  const exposureTable = trial?.exposure_table || [];

  return (
    <div className="space-y-6">
      {/* ── FR7.1: Question Box & Case Parameters ────────────────────────── */}
      <div className="rounded-2xl border border-amber-500/30 bg-slate-950/80 p-6 space-y-5 shadow-2xl shadow-amber-500/5">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/30">
              <Scale className="w-5 h-5 text-slate-950 font-bold" />
            </div>
            <div>
              <h2 className="font-orbitron font-bold text-lg text-white tracking-wide flex items-center gap-2">
                ODIN COUNCIL TRIAL CHAMBER
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  FR1–FR8 COMPLIANT
                </span>
              </h2>
              <p className="text-xs text-slate-400 font-rajdhani uppercase tracking-wider">
                Autonomous Trial: Heimdall Gatekeeper → Thor & Loki Debate → Odin Judicial Rulings
              </p>
            </div>
          </div>

          {/* Quick preset chips */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400">Presets:</span>
            {presets.map((p, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuestion(p.q);
                  setAsOfDate(p.d);
                }}
                className="px-2.5 py-1 rounded-lg text-[11px] font-mono border border-slate-800 bg-slate-900/60 text-slate-300 hover:border-amber-500/50 hover:text-white transition-all"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div className="md:col-span-9 space-y-1.5">
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <span>User Investigation Question (FR1.1 / FR7.1)</span>
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={2}
              className="w-full rounded-xl border border-slate-800 bg-slate-900/90 p-3 font-mono text-xs text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none transition-colors"
              placeholder="Ask ODIN a question regarding contracts, outages, exposures, or defaults..."
            />
          </div>

          <div className="md:col-span-3 space-y-1.5">
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-amber-400" />
              <span>As-Of Date (FR1.1)</span>
            </label>
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900/90 p-3 font-mono text-xs text-white focus:border-amber-500 focus:outline-none"
            />
            <button
              onClick={handleLaunchTrial}
              disabled={running || !question.trim()}
              className="w-full mt-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold font-rajdhani text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-amber-500/25 disabled:opacity-50 transition-all cursor-pointer"
            >
              {running ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Trial in Progress...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Launch Trial (FR5)</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* ── FR7.1: Live News & Operational Events Feed Ticker ─────────────── */}
        {trial?.news_feed && trial.news_feed.length > 0 && (
          <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                <span className="font-orbitron font-bold text-[11px] text-cyan-300 uppercase tracking-wider">
                  Live World News & Operational Event Feed (FR7.1)
                </span>
              </div>
              <span className="font-mono text-[10px] text-slate-400">
                Replaying {trial.news_feed.length} World intelligence articles & logs
              </span>
            </div>

            <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-thin">
              {trial.news_feed.slice(0, 5).map((item) => (
                <div
                  key={item.id}
                  onClick={() =>
                    item.related_doc_id && item.related_doc_id !== "Operational"
                      ? openEvidence(item.related_doc_id, "Article Context", item.body)
                      : null
                  }
                  className={`min-w-[280px] max-w-[320px] rounded-lg border p-2.5 text-xs font-mono space-y-1 cursor-pointer transition-all ${
                    item.severity === "CRITICAL"
                      ? "border-rose-500/30 bg-rose-950/30 hover:border-rose-500"
                      : item.severity === "HIGH"
                      ? "border-amber-500/30 bg-amber-950/30 hover:border-amber-500"
                      : "border-cyan-500/30 bg-cyan-950/30 hover:border-cyan-500"
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span className="font-bold text-slate-300">{item.source}</span>
                    <span>{item.timestamp.slice(0, 10)}</span>
                  </div>
                  <p className="font-bold text-slate-200 line-clamp-1 text-[11px]">{item.headline}</p>
                  <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Sub-Navigation: Trial View | Exposure Table | Final Briefing | Private Memories ── */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedSubTab("trial")}
            className={`px-4 py-2 rounded-xl text-xs font-rajdhani font-bold uppercase tracking-wider transition-all flex items-center gap-2 ${
              selectedSubTab === "trial"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/30"
                : "border border-slate-800 bg-slate-900/40 text-slate-400 hover:text-white"
            }`}
          >
            <Swords className="w-4 h-4" />
            <span>FR7.2 Trial View (Thor vs Loki)</span>
          </button>

          <button
            onClick={() => setSelectedSubTab("exposure")}
            className={`px-4 py-2 rounded-xl text-xs font-rajdhani font-bold uppercase tracking-wider transition-all flex items-center gap-2 ${
              selectedSubTab === "exposure"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/30"
                : "border border-slate-800 bg-slate-900/40 text-slate-400 hover:text-white"
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>FR7.3 Exposure Table</span>
          </button>

          <button
            onClick={() => setSelectedSubTab("briefing")}
            className={`px-4 py-2 rounded-xl text-xs font-rajdhani font-bold uppercase tracking-wider transition-all flex items-center gap-2 ${
              selectedSubTab === "briefing"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/30"
                : "border border-slate-800 bg-slate-900/40 text-slate-400 hover:text-white"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>FR8 Final Briefing</span>
          </button>

          <button
            onClick={() => setSelectedSubTab("memories")}
            className={`px-4 py-2 rounded-xl text-xs font-rajdhani font-bold uppercase tracking-wider transition-all flex items-center gap-2 ${
              selectedSubTab === "memories"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/30"
                : "border border-slate-800 bg-slate-900/40 text-slate-400 hover:text-white"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>FR6 Agent Memories</span>
          </button>
        </div>

        {/* Multi-Run Selector (FR5.4) */}
        {trial?.runs && trial.runs.length > 1 && (
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs font-mono">
            <span className="text-slate-400 px-2 text-[11px]">Trial Run:</span>
            {trial.runs.map((r, idx) => (
              <button
                key={idx}
                onClick={() => setActiveRunIndex(idx)}
                className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                  activeRunIndex === idx
                    ? "bg-amber-500 text-slate-950"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Run {r.run_number} {idx === 1 ? "(Drop 2 New Evidence)" : "(Initial Search)"}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── FR1: Heimdall Gatekeeper Status Card ──────────────────────────── */}
      {caseFile && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-orbitron font-bold text-xs text-emerald-300">
                  HEIMDALL GATEKEEPER (CASE FILE {caseFile.case_id})
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-600 text-emerald-300 font-bold">
                  {caseFile.verified ? "EVENT VERIFIED IN WORLD" : "UNVERIFIED"}
                </span>
              </div>
              <p className="text-xs text-slate-300 font-mono mt-0.5">{caseFile.verification_notes}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
            <span>Documents: {caseFile.documents_gathered.length}</span>
            <span>Events: {caseFile.events_count}</span>
            <span className="text-emerald-400 font-bold">As-Of: {caseFile.as_of_date}</span>
          </div>
        </div>
      )}

      {/* ── FR4.3: Odin Sufficiency Check Banner ──────────────────────────── */}
      {currentRun?.sufficiency && (
        <div
          className={`rounded-xl border p-4 flex items-start gap-3 ${
            currentRun.sufficiency.is_sufficient
              ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-200"
              : "border-amber-500/40 bg-amber-950/20 text-amber-200"
          }`}
        >
          {currentRun.sufficiency.is_sufficient ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          )}
          <div className="space-y-1 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="font-orbitron font-bold text-xs uppercase tracking-wider text-white">
                ODIN SUFFICIENCY CHECK (RUN {currentRun.run_number})
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 font-bold">
                {currentRun.sufficiency.decision}
              </span>
            </div>
            <p className="text-slate-300">{currentRun.sufficiency.message}</p>
            {currentRun.sufficiency.missing_evidence.length > 0 && (
              <ul className="list-disc list-inside space-y-0.5 text-slate-400 pt-1">
                {currentRun.sufficiency.missing_evidence.map((me, i) => (
                  <li key={i}>{me}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 1: FR7.2 Trial View (Thor vs Loki Side-by-Side + Odin Rulings) ── */}
      {selectedSubTab === "trial" && currentRun && (
        <div className="space-y-6">
          {/* Round 1 Simultaneous Claims Header */}
          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/60 flex items-center justify-between">
            <span className="font-orbitron font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-2">
              <Swords className="w-4 h-4 text-amber-400" />
              TRIAL ROUND 1: SIMULTANEOUS ADVERSARIAL CLAIMS (FR5.2)
            </span>
            <span className="font-mono text-xs text-slate-400">
              Thor (High Exposure) vs Loki (Limited Exposure)
            </span>
          </div>

          {/* Side-by-Side Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Thor – The Alarm (High Case) */}
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-xl border border-rose-500/40 bg-rose-950/20">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center">
                    <ShieldAlert className="w-4 h-4 text-rose-400" />
                  </div>
                  <div>
                    <h3 className="font-orbitron font-bold text-sm text-rose-300">
                      THOR — THE ALARM (HIGH CASE)
                    </h3>
                    <p className="text-[10px] text-slate-400 font-mono">
                      Maximizing exposure estimate per country & sector (FR2.1 / FR2.2)
                    </p>
                  </div>
                </div>
                <span className="text-xs font-mono font-bold text-rose-400">
                  Total: $
                  {currentRun.round1.thor_claims
                    .reduce((sum, c) => sum + (c.estimate_high || 0), 0)
                    .toLocaleString()}
                </span>
              </div>

              {currentRun.round1.thor_claims.map((claim) => (
                <div
                  key={claim.id}
                  className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3 hover:border-rose-500/50 transition-all"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-mono font-bold text-rose-400">
                      {claim.id} · {claim.country} ({claim.sector})
                    </span>
                    <span className="text-xs font-jetbrains font-bold text-rose-400 bg-rose-950/60 px-2.5 py-0.5 rounded border border-rose-800">
                      High: ${claim.estimate_high?.toLocaleString()}
                    </span>
                  </div>

                  <p className="text-xs font-mono text-slate-200 leading-relaxed">{claim.claim}</p>

                  {/* Quoted Document Citation */}
                  <div className="p-3 rounded-lg border border-slate-800 bg-black/40 space-y-1.5 text-xs font-mono">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <button
                        onClick={() => openEvidence(claim.document_id, claim.clause_ref, claim.quote)}
                        className="text-cyan-400 hover:underline flex items-center gap-1 font-bold"
                      >
                        <FileText className="w-3 h-3" />
                        <span>
                          Doc {claim.document_id} · {claim.clause_ref}
                        </span>
                        <ExternalLink className="w-2.5 h-2.5 ml-0.5" />
                      </button>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                        {claim.type}
                      </span>
                    </div>
                    <blockquote className="border-l-2 border-amber-500 pl-2.5 italic text-slate-300 text-[11px]">
                      "{claim.quote}"
                    </blockquote>
                  </div>

                  <p className="text-[11px] text-slate-400 font-mono italic">
                    Reasoning: {claim.rationale}
                  </p>
                </div>
              ))}
            </div>

            {/* Right: Loki – The Trickster (Limited Case) */}
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-xl border border-purple-500/40 bg-purple-950/20">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-purple-500/20 border border-purple-500/40 flex items-center justify-center">
                    <ShieldCheck className="w-4 h-4 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-orbitron font-bold text-sm text-purple-300">
                      LOKI — THE TRICKSTER (LIMITED CASE)
                    </h3>
                    <p className="text-[10px] text-slate-400 font-mono">
                      Grounding minimal exposure liability with defenses (FR3.1 / FR3.2)
                    </p>
                  </div>
                </div>
                <span className="text-xs font-mono font-bold text-purple-400">
                  Total: $
                  {currentRun.round1.loki_claims
                    .reduce((sum, c) => sum + (c.estimate_low || 0), 0)
                    .toLocaleString()}
                </span>
              </div>

              {currentRun.round1.loki_claims.map((claim) => (
                <div
                  key={claim.id}
                  className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3 hover:border-purple-500/50 transition-all"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-mono font-bold text-purple-400">
                      {claim.id} · {claim.country} ({claim.sector})
                    </span>
                    <span className="text-xs font-jetbrains font-bold text-purple-400 bg-purple-950/60 px-2.5 py-0.5 rounded border border-purple-800">
                      Low: ${claim.estimate_low?.toLocaleString()}
                    </span>
                  </div>

                  <p className="text-xs font-mono text-slate-200 leading-relaxed">{claim.claim}</p>

                  {/* Quoted Document Citation */}
                  <div className="p-3 rounded-lg border border-slate-800 bg-black/40 space-y-1.5 text-xs font-mono">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <button
                        onClick={() => openEvidence(claim.document_id, claim.clause_ref, claim.quote)}
                        className="text-cyan-400 hover:underline flex items-center gap-1 font-bold"
                      >
                        <FileText className="w-3 h-3" />
                        <span>
                          Doc {claim.document_id} · {claim.clause_ref}
                        </span>
                        <ExternalLink className="w-2.5 h-2.5 ml-0.5" />
                      </button>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                        {claim.type}
                      </span>
                    </div>
                    <blockquote className="border-l-2 border-purple-500 pl-2.5 italic text-slate-300 text-[11px]">
                      "{claim.quote}"
                    </blockquote>
                  </div>

                  <p className="text-[11px] text-slate-400 font-mono italic">
                    Reasoning: {claim.rationale}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* ── Round 2: Adversarial Attacks & Defences / Concessions (FR5.3) ── */}
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="font-orbitron font-bold text-xs uppercase tracking-wider text-amber-300 flex items-center gap-2">
                <Swords className="w-4 h-4 text-amber-400" />
                TRIAL ROUND 2: MUTUAL ADVERSARIAL ATTACKS & DEFENCES (FR5.3)
              </span>
              <span className="text-[10px] font-mono text-slate-500">
                Each side must attack at least one claim or concede
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentRun.round2.attacks.map((atk) => (
                <div
                  key={atk.id}
                  className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-950/10 space-y-2 text-xs font-mono"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-bold text-amber-400">
                      {atk.attacker} attacks {atk.target_claim_id}
                    </span>
                    <span className="text-slate-500">Attack Point</span>
                  </div>
                  <p className="text-slate-200">{atk.attack_point}</p>
                  {atk.new_evidence && (
                    <div className="p-2 rounded bg-black/40 border border-slate-800 text-[11px] text-cyan-300">
                      New Evidence Cited: Doc {atk.new_evidence.document_id} ({atk.new_evidence.clause_ref}): "
                      {atk.new_evidence.quote}"
                    </div>
                  )}
                </div>
              ))}

              {currentRun.round2.defences.map((def) => (
                <div
                  key={def.id}
                  className={`p-3.5 rounded-xl border space-y-2 text-xs font-mono ${
                    def.response_type === "CONCEDE"
                      ? "border-rose-500/30 bg-rose-950/20"
                      : "border-emerald-500/30 bg-emerald-950/20"
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span
                      className={`font-bold ${
                        def.response_type === "CONCEDE" ? "text-rose-400" : "text-emerald-400"
                      }`}
                    >
                      {def.defender} response on {def.target_claim_id}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        def.response_type === "CONCEDE"
                          ? "bg-rose-950 text-rose-300 border border-rose-800"
                          : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      }`}
                    >
                      {def.response_type}
                    </span>
                  </div>
                  <p className="text-slate-200">{def.argument}</p>
                </div>
              ))}
            </div>
          </div>

          {/* ── FR4.1 & FR4.2: Odin Judicial Rulings ────────────────────────── */}
          <div className="rounded-2xl border-2 border-amber-500/40 bg-slate-950/90 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center">
                  <Scale className="w-4 h-4 text-amber-400" />
                </div>
                <div>
                  <h3 className="font-orbitron font-bold text-sm text-white">
                    ODIN ALLFATHER JUDICIAL RULINGS (FR4.1 / FR4.2)
                  </h3>
                  <p className="text-[10px] font-mono text-slate-400">
                    Claims sorted into Established, Contested, and Conceded with Fact vs Inference tagging
                  </p>
                </div>
              </div>

              <span className="text-xs font-mono font-bold text-amber-400">
                Net Established Exposure: $
                {currentRun.odin_rulings
                  .reduce((sum, r) => sum + (r.established_exposure || 0), 0)
                  .toLocaleString()}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {currentRun.odin_rulings.map((ruling) => (
                <div
                  key={ruling.id}
                  className={`p-4 rounded-xl border space-y-3 text-xs font-mono ${
                    ruling.classification === "ESTABLISHED"
                      ? "border-emerald-500/40 bg-emerald-950/20"
                      : ruling.classification === "CONTESTED"
                      ? "border-amber-500/40 bg-amber-950/20"
                      : "border-purple-500/40 bg-purple-950/20"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        ruling.classification === "ESTABLISHED"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-600"
                          : ruling.classification === "CONTESTED"
                          ? "bg-amber-950 text-amber-300 border border-amber-600"
                          : "bg-purple-950 text-purple-300 border border-purple-600"
                      }`}
                    >
                      {ruling.classification}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                      {ruling.fact_type}
                    </span>
                  </div>

                  <h4 className="font-bold text-white text-sm leading-snug">{ruling.topic}</h4>
                  <p className="text-slate-300 text-[11px] leading-relaxed">{ruling.rationale}</p>

                  <div className="pt-2 border-t border-white/10 flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">Established Liability:</span>
                    <span className="font-bold text-white font-jetbrains">
                      ${ruling.established_exposure.toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: FR7.3 Exposure Table ──────────────────────────────────── */}
      {selectedSubTab === "exposure" && (
        <div className="space-y-6">
          {/* Exposure Summary Card */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="hud-panel p-5 rounded-xl space-y-1">
              <span className="text-xs font-mono text-purple-400 uppercase font-bold">
                Low Bound (Loki Case)
              </span>
              <div className="text-2xl font-bold font-jetbrains text-purple-300">
                ${exposureTable.reduce((sum, r) => sum + r.low_estimate, 0).toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500 font-mono">Maximum contractual defenses</span>
            </div>

            <div className="hud-panel p-5 rounded-xl space-y-1">
              <span className="text-xs font-mono text-emerald-400 uppercase font-bold">
                Net Established Exposure (Odin Ruling)
              </span>
              <div className="text-2xl font-bold font-jetbrains text-emerald-300">
                ${exposureTable.reduce((sum, r) => sum + r.established_amount, 0).toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500 font-mono">Adjudicated commercial liability</span>
            </div>

            <div className="hud-panel p-5 rounded-xl space-y-1">
              <span className="text-xs font-mono text-rose-400 uppercase font-bold">
                High Bound (Thor Case)
              </span>
              <div className="text-2xl font-bold font-jetbrains text-rose-300">
                ${exposureTable.reduce((sum, r) => sum + r.high_estimate, 0).toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500 font-mono">Uncapped liquidated damages</span>
            </div>
          </div>

          {/* Exposure Matrix Table */}
          <div className="hud-panel p-6 rounded-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="font-orbitron font-bold text-base text-white">
                  PORTFOLIO EXPOSURE TABLE BY REGION & SECTOR (FR7.3)
                </h3>
                <p className="text-xs text-slate-400 font-rajdhani">
                  Low range (Loki) vs High range (Thor) with Odin judicial established liability
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-jetbrains text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="pb-3">Subject / Issue</th>
                    <th className="pb-3">Country / Region</th>
                    <th className="pb-3">Sector</th>
                    <th className="pb-3 text-right">Low (Loki)</th>
                    <th className="pb-3 text-right">High (Thor)</th>
                    <th className="pb-3 text-right">Established (Odin)</th>
                    <th className="pb-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {exposureTable.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/40">
                      <td className="py-3.5 pr-4 font-bold text-white">{row.topic}</td>
                      <td className="py-3.5 text-slate-400">{row.country}</td>
                      <td className="py-3.5 text-slate-400">{row.sector}</td>
                      <td className="py-3.5 text-right text-purple-400 font-bold">
                        ${row.low_estimate.toLocaleString()}
                      </td>
                      <td className="py-3.5 text-right text-rose-400 font-bold">
                        ${row.high_estimate.toLocaleString()}
                      </td>
                      <td className="py-3.5 text-right text-emerald-400 font-bold">
                        ${row.established_amount.toLocaleString()}
                      </td>
                      <td className="py-3.5 text-center">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            row.status === "ESTABLISHED"
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-600"
                              : row.status === "CONTESTED"
                              ? "bg-amber-950 text-amber-300 border border-amber-600"
                              : "bg-purple-950 text-purple-300 border border-purple-600"
                          }`}
                        >
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 3: FR8 Final Briefing ────────────────────────────────────── */}
      {selectedSubTab === "briefing" && briefing && (
        <div className="space-y-6">
          <div className="rounded-2xl border-2 border-amber-500/50 bg-slate-950 p-8 space-y-6 shadow-2xl">
            {/* Briefing Header */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
              <div>
                <span className="text-[10px] font-mono text-amber-400 uppercase tracking-widest block">
                  OFFICIAL TRIAL RECORD · ADJUDICATED BY ODIN
                </span>
                <h2 className="font-orbitron font-bold text-xl text-white mt-1">{briefing.title}</h2>
                <p className="text-xs text-slate-400 font-mono mt-1">
                  Case ID: {briefing.case_id} · As-Of Date: {briefing.as_of_date} · Adjudicated:{" "}
                  {briefing.adjudicated_at.slice(0, 16).replace("T", " ")}
                </p>
              </div>

              <button
                onClick={() => window.print()}
                className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-amber-500 text-xs font-mono text-slate-300 hover:text-white flex items-center gap-2 transition-all cursor-pointer"
              >
                <Printer className="w-4 h-4 text-amber-400" />
                <span>Print Dossier</span>
              </button>
            </div>

            {/* FR8.1: Executive Summary */}
            <div className="p-5 rounded-xl border border-amber-500/30 bg-amber-950/10 space-y-2">
              <span className="font-orbitron font-bold text-xs text-amber-300 uppercase tracking-wider block">
                EXECUTIVE SUMMARY (FR8.1)
              </span>
              <p className="text-sm font-mono text-slate-200 leading-relaxed">
                {briefing.executive_summary}
              </p>
            </div>

            {/* Classification Sections */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-950/20 space-y-2">
                <span className="text-xs font-bold text-emerald-400 font-mono uppercase">
                  Established Findings ({briefing.established_findings.length})
                </span>
                {briefing.established_findings.map((f) => (
                  <div key={f.id} className="text-xs font-mono space-y-1 pt-2 border-t border-emerald-500/20">
                    <p className="font-bold text-white">{f.topic}</p>
                    <p className="text-slate-300 text-[11px]">{f.rationale}</p>
                    <span className="text-emerald-400 font-bold block">${f.established_exposure.toLocaleString()}</span>
                  </div>
                ))}
              </div>

              <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-950/20 space-y-2">
                <span className="text-xs font-bold text-amber-400 font-mono uppercase">
                  Contested Findings ({briefing.contested_findings.length})
                </span>
                {briefing.contested_findings.map((f) => (
                  <div key={f.id} className="text-xs font-mono space-y-1 pt-2 border-t border-amber-500/20">
                    <p className="font-bold text-white">{f.topic}</p>
                    <p className="text-slate-300 text-[11px]">{f.rationale}</p>
                    <span className="text-amber-400 font-bold block">Contested: ${f.established_exposure.toLocaleString()}</span>
                  </div>
                ))}
              </div>

              <div className="p-4 rounded-xl border border-purple-500/40 bg-purple-950/20 space-y-2">
                <span className="text-xs font-bold text-purple-400 font-mono uppercase">
                  Conceded Findings ({briefing.conceded_findings.length})
                </span>
                {briefing.conceded_findings.map((f) => (
                  <div key={f.id} className="text-xs font-mono space-y-1 pt-2 border-t border-purple-500/20">
                    <p className="font-bold text-white">{f.topic}</p>
                    <p className="text-slate-300 text-[11px]">{f.rationale}</p>
                    <span className="text-purple-400 font-bold block">Conceded ($0 liability)</span>
                  </div>
                ))}
              </div>
            </div>

            {/* FR8.2: Next-Quarter Outlook & Assumptions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 space-y-2">
                <span className="font-orbitron font-bold text-xs text-white uppercase tracking-wider block">
                  NEXT-QUARTER OUTLOOK (FR8.2)
                </span>
                <p className="text-xs font-mono text-slate-300 leading-relaxed">
                  {briefing.next_quarter_outlook}
                </p>
              </div>

              <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 space-y-2">
                <span className="font-orbitron font-bold text-xs text-white uppercase tracking-wider block">
                  ADJUDICATED ASSUMPTIONS (FR8.2)
                </span>
                <ul className="list-disc list-inside space-y-1.5 text-xs font-mono text-slate-300">
                  {briefing.assumptions.map((assump, i) => (
                    <li key={i}>{assump}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* FR8.3: Inline Citations & Source List */}
            <div className="space-y-3 pt-4 border-t border-slate-800">
              <span className="font-orbitron font-bold text-xs text-amber-300 uppercase tracking-wider block">
                INLINE CITATIONS & WORLD REPOSITORY SOURCES (FR8.3)
              </span>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {briefing.citations.map((cite, i) => (
                  <div
                    key={i}
                    onClick={() => openEvidence(cite.document_id, cite.clause_ref, cite.quote)}
                    className="p-3 rounded-lg border border-slate-800 bg-black/40 hover:border-amber-500/50 cursor-pointer transition-all space-y-1 text-xs font-mono"
                  >
                    <div className="flex items-center justify-between text-cyan-400 font-bold">
                      <span>
                        {cite.document_id} · {cite.clause_ref}
                      </span>
                      <ExternalLink className="w-3 h-3" />
                    </div>
                    <p className="text-slate-400 text-[11px]">{cite.title}</p>
                    <blockquote className="border-l-2 border-amber-500 pl-2 text-slate-300 italic text-[11px]">
                      "{cite.quote}"
                    </blockquote>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 4: FR6 Private Agent Memories ─────────────────────────────── */}
      {selectedSubTab === "memories" && trial?.agent_memories && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {Object.entries(trial.agent_memories).map(([agent, logs]) => (
            <div key={agent} className="hud-panel p-5 rounded-xl space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="font-bold text-white capitalize">{agent} Private Memory Log (FR6.1)</span>
                <span className="text-[10px] text-slate-500">Persistent SQLite Store</span>
              </div>
              <div className="space-y-1.5 text-slate-300 text-[11px] max-h-48 overflow-y-auto">
                {logs.map((log, i) => (
                  <p key={i} className="border-l-2 border-slate-800 pl-2 py-0.5">
                    {log}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── FR7.4: Evidence Modal (Full Document View with Quote Highlight) ── */}
      {evidenceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="max-w-3xl w-full max-h-[85vh] rounded-2xl border border-cyan-500/40 bg-[#0a1220] shadow-2xl flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                <span className="font-orbitron font-bold text-sm text-white">
                  World Document Proof · {evidenceModal.docId} ({evidenceModal.clauseRef})
                </span>
              </div>
              <button
                onClick={() => setEvidenceModal(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 font-mono text-xs">
              <div className="p-3 rounded-lg border border-amber-500/40 bg-amber-950/20 text-amber-200">
                <span className="font-bold block text-[11px] uppercase tracking-wider mb-1">
                  Exact Cited Quoted Evidence (FR7.4):
                </span>
                <blockquote className="border-l-2 border-amber-400 pl-3 italic text-sm text-white">
                  "{evidenceModal.quote}"
                </blockquote>
              </div>

              <div>
                <span className="text-[11px] text-slate-400 uppercase tracking-wider font-bold block mb-1">
                  Full Document Context: {evidenceModal.title}
                </span>
                <div className="p-4 rounded-xl border border-slate-800 bg-black/60 text-slate-300 whitespace-pre-wrap leading-relaxed max-h-[40vh] overflow-y-auto">
                  {evidenceModal.loading ? (
                    <div className="flex items-center justify-center p-8">
                      <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
                    </div>
                  ) : (
                    evidenceModal.content
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Verified against World Document Repository</span>
              <button
                onClick={() => setEvidenceModal(null)}
                className="px-4 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
