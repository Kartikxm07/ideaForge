"use client";

import React, { useState } from "react";
import {
  Scale,
  ShieldAlert,
  Eye,
  FileText,
  ChevronDown,
  ChevronRight,
  Filter,
  RefreshCw,
  Play,
  Pause,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";

export function DebateView() {
  const { conflicts, openEvidence } = useOdinStore();
  const [filterDisagreementsOnly, setFilterDisagreementsOnly] = useState(false);
  const [collapsedClarifications, setCollapsedClarifications] = useState<Record<string, boolean>>({
    "CONF-01": false,
  });
  const [isSimulatingStream, setIsSimulatingStream] = useState(true);

  const toggleClarification = (id: string) => {
    setCollapsedClarifications((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const filteredConflicts = conflicts.filter((c) => {
    if (filterDisagreementsOnly && c.heimdallVerification === "VERIFIED") return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header & Stream Simulation Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-cyan-500/20 bg-slate-950/60">
        <div>
          <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
            <Scale className="w-5 h-5 text-rose-400" />
            COUNCIL DEBATE CHAMBER & ADJUDICATION ARBITER
          </h3>
          <p className="text-xs text-slate-400 font-rajdhani uppercase tracking-wider">
            Loki adversarial attack hypotheses tested by Heimdall event evidence and ruled by Tyr
          </p>
        </div>

        {/* Filter & Stream Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFilterDisagreementsOnly(!filterDisagreementsOnly)}
            className={`px-3 py-1.5 rounded-lg text-xs font-rajdhani font-bold transition-all border ${
              filterDisagreementsOnly
                ? "border-amber-400 bg-amber-950/60 text-amber-300"
                : "border-slate-800 bg-slate-900/40 text-slate-400 hover:text-white"
            }`}
          >
            Disagreements Only ({conflicts.filter((c) => c.heimdallVerification !== "VERIFIED").length})
          </button>

          <button
            onClick={() => setIsSimulatingStream(!isSimulatingStream)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950 border border-cyan-500/40 text-cyan-300 text-xs font-mono font-bold hover:bg-cyan-900/60 transition-all"
          >
            {isSimulatingStream ? (
              <>
                <Pause className="w-3.5 h-3.5 text-cyan-400" />
                <span>Pause Agent Stream</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 text-cyan-400" />
                <span>Resume Stream</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Threaded Debate Cards */}
      <div className="space-y-6">
        {filteredConflicts.map((conf, idx) => (
          <div
            key={conf.id}
            className="hud-panel rounded-2xl p-6 space-y-5 border-slate-800 hover:border-slate-700 transition-all"
          >
            {/* Debate Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <Badge
                  variant="destructive"
                  className={
                    conf.severity === "CRITICAL"
                      ? "bg-rose-950 text-rose-400 border-rose-800"
                      : "bg-amber-950 text-amber-400 border-amber-800"
                  }
                >
                  {conf.severity}
                </Badge>
                <span className="font-jetbrains text-sm font-bold text-white">
                  {conf.id}: {conf.title}
                </span>
              </div>

              {/* Loop Counter Pill */}
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                  Round 2/3 • Clarifications: {conf.clarifications?.length || 0}/2
                </span>
                <span className="text-rose-400 font-bold font-jetbrains">
                  ${conf.financialExposure.toLocaleString()} Exposure
                </span>
              </div>
            </div>

            {/* Stage 1: Loki Adversarial Attack */}
            <div className="p-4 rounded-xl border border-purple-500/30 bg-purple-950/20 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
                  <span className="font-rajdhani font-bold text-xs uppercase tracking-wider text-purple-300">
                    STAGE 1: LOKI ADVERSARIAL ATTACK HYPOTHESIS
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEvidence(conf.sourceClauseId)}
                    className="text-[11px] font-mono text-purple-300 hover:underline flex items-center gap-1"
                  >
                    <FileText className="w-3 h-3" />
                    <span>Clause {conf.sourceClauseId}</span>
                  </button>
                  <button
                    onClick={() => openEvidence(conf.targetClauseId)}
                    className="text-[11px] font-mono text-purple-300 hover:underline flex items-center gap-1"
                  >
                    <FileText className="w-3 h-3" />
                    <span>Clause {conf.targetClauseId}</span>
                  </button>
                </div>
              </div>
              <p className="text-xs font-mono text-purple-100 leading-relaxed">
                {conf.lokiArgument}
              </p>
            </div>

            {/* Collapsible Sub-Thread: Loki <-> Thor Targeted Clarification */}
            {conf.clarifications && conf.clarifications.length > 0 && (
              <div className="pl-6 border-l-2 border-dashed border-cyan-500/40 space-y-3">
                <button
                  onClick={() => toggleClarification(conf.id)}
                  className="flex items-center gap-2 text-xs font-mono font-bold text-cyan-400 hover:text-cyan-300"
                >
                  {collapsedClarifications[conf.id] ? (
                    <ChevronRight className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                  <span>
                    Loki ↔ Thor Targeted Clarification Thread ({conf.clarifications.length} exchanges)
                  </span>
                </button>

                {!collapsedClarifications[conf.id] && (
                  <div className="space-y-3 pt-1">
                    {conf.clarifications.map((cl, i) => (
                      <div
                        key={i}
                        className="p-3.5 rounded-lg border border-cyan-500/30 bg-cyan-950/20 text-xs font-mono space-y-2"
                      >
                        <div className="flex items-center justify-between text-slate-400 text-[11px]">
                          <span>Round {cl.round}: Loki asks Thor</span>
                          <span className="text-emerald-400 font-bold">
                            Confidence: {(cl.confidenceDelta[0] * 100).toFixed(0)}% →{" "}
                            {(cl.confidenceDelta[1] * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-slate-300 font-bold">Q: {cl.question}</p>
                        <p className="text-cyan-200">A: {cl.answer}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Stage 2: Heimdall Event & Incident Verification */}
            <div className="p-4 rounded-xl border border-teal-500/30 bg-teal-950/20 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-400" />
                  <span className="font-rajdhani font-bold text-xs uppercase tracking-wider text-teal-300">
                    STAGE 2: HEIMDALL OPERATIONAL EVENT VERIFICATION
                  </span>
                </div>
                <Badge
                  className={`text-xs font-mono font-bold ${
                    conf.heimdallVerification === "VERIFIED"
                      ? "bg-emerald-950 text-emerald-300 border-emerald-600"
                      : "bg-amber-950 text-amber-300 border-amber-600"
                  }`}
                >
                  {conf.heimdallVerification} EVIDENCE
                </Badge>
              </div>
              <p className="text-xs font-mono text-teal-100 leading-relaxed">
                {conf.heimdallNotes}
              </p>
            </div>

            {/* Stage 3: Tyr Traceable Ruling & Action Drafting */}
            <div className="p-4 rounded-xl border-2 border-rose-500/50 bg-rose-950/20 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Scale className="w-4 h-4 text-rose-400" />
                  <span className="font-rajdhani font-bold text-xs uppercase tracking-wider text-rose-300">
                    STAGE 3: TYR ADJUDICATION RULING
                  </span>
                </div>
                <Badge className="bg-rose-900 text-rose-100 border-rose-600 font-mono text-xs">
                  VERDICT: {conf.tyrRuling}
                </Badge>
              </div>
              <p className="text-xs font-mono text-slate-200 leading-relaxed">
                {conf.tyrRationale}
              </p>
              <div className="p-2.5 rounded bg-black/40 border border-white/10 text-xs font-mono text-cyan-300 mt-2">
                Drafted Mandate: {conf.recommendedAction}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
