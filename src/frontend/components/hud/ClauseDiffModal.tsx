"use client";

import React from "react";
import { X, Scale, AlertOctagon, ArrowRight, ShieldAlert } from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";

export function ClauseDiffModal() {
  const { diffConflictId, closeDiff, conflicts, clauses, openEvidence } = useOdinStore();

  const conflict = conflicts.find((c) => c.id === diffConflictId);

  if (!conflict) return null;

  const sourceClause = clauses.find((c) => c.id === conflict.sourceClauseId);
  const targetClause = clauses.find((c) => c.id === conflict.targetClauseId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4">
      {/* Backdrop */}
      <div className="absolute inset-0" onClick={closeDiff} />

      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#070b14] border border-cyan-500/40 rounded-2xl p-6 shadow-2xl flex flex-col justify-between overflow-y-auto">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-slate-800 pb-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Badge
                  variant="destructive"
                  className={
                    conflict.severity === "CRITICAL"
                      ? "bg-rose-950 text-rose-400 border-rose-800"
                      : "bg-amber-950 text-amber-400 border-amber-800"
                  }
                >
                  {conflict.severity} CONFLICT
                </Badge>
                <span className="font-mono text-xs text-slate-400">
                  {conflict.sourceDoc} ↔ {conflict.targetDoc}
                </span>
              </div>
              <h3 className="font-orbitron font-bold text-lg text-white">
                {conflict.title}
              </h3>
              <p className="text-xs text-slate-400 font-rajdhani uppercase tracking-wider mt-0.5" suppressHydrationWarning>
                Financial Exposure: ${conflict.financialExposure.toLocaleString("en-US")} • Likelihood: {conflict.likelihood}%
              </p>
            </div>

            <button
              onClick={closeDiff}
              className="p-1 rounded-lg border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Side-by-Side Clause Texts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left: Source Document Clause */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-jetbrains font-bold text-xs text-cyan-300">
                  SOURCE: {conflict.sourceDoc} ({conflict.sourceClauseId})
                </span>
                {sourceClause && (
                  <button
                    onClick={() => {
                      closeDiff();
                      openEvidence(conflict.sourceClauseId);
                    }}
                    className="text-[10px] text-cyan-400 hover:underline"
                  >
                    View Evidence →
                  </button>
                )}
              </div>
              <p className="text-xs font-mono text-slate-300 leading-relaxed p-3 rounded bg-slate-950 border border-slate-900">
                {sourceClause?.text || "Upstream hosting terms limit maximum service credit to 15% of monthly fees for uptime defaults."}
              </p>
            </div>

            {/* Right: Target Document Clause */}
            <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-950/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-jetbrains font-bold text-xs text-rose-300">
                  CONTRADICTING: {conflict.targetDoc} ({conflict.targetClauseId})
                </span>
                {targetClause && (
                  <button
                    onClick={() => {
                      closeDiff();
                      openEvidence(conflict.targetClauseId);
                    }}
                    className="text-[10px] text-rose-400 hover:underline"
                  >
                    View Evidence →
                  </button>
                )}
              </div>
              <p className="text-xs font-mono text-slate-300 leading-relaxed p-3 rounded bg-slate-950 border border-slate-900">
                {targetClause?.text || "Customer agreement mandates 50% withholding plus $15,000 per day liquidated damages for availability failure."}
              </p>
            </div>
          </div>

          {/* Loki Attack Vector & Tyr Adjudication */}
          <div className="space-y-3">
            <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-950/20 text-xs text-amber-200">
              <span className="font-bold text-amber-400 block mb-1 font-rajdhani uppercase tracking-wider">
                LOKI ADVERSARIAL ATTACK PATH
              </span>
              {conflict.lokiArgument}
            </div>

            <div className="p-3.5 rounded-xl border border-cyan-500/30 bg-cyan-950/20 text-xs text-cyan-200">
              <span className="font-bold text-cyan-400 block mb-1 font-rajdhani uppercase tracking-wider">
                TYR LEGAL RULING & RECOMMENDED MITIGATION
              </span>
              <p className="mb-1.5">{conflict.tyrRationale}</p>
              <p className="font-bold text-white">Action: {conflict.recommendedAction}</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-slate-800 flex justify-end">
          <button
            onClick={closeDiff}
            className="px-5 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-rajdhani font-bold text-xs uppercase tracking-wider"
          >
            Acknowledge Discrepancy
          </button>
        </div>
      </div>
    </div>
  );
}
