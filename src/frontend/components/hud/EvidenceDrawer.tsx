"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  ShieldCheck,
  Brain,
  Paperclip,
  AlertCircle,
  Hash,
  Clock,
  Layers,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";

export function EvidenceDrawer() {
  const { evidenceClauseId, closeEvidence, clauses } = useOdinStore();

  const clause = clauses.find((c) => c.id === evidenceClauseId);

  if (!clause) return null;

  const renderBadgeType = () => {
    switch (clause.evidenceType) {
      case "SOURCED":
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded border border-cyan-400 bg-cyan-950/60 text-cyan-300 text-xs font-mono font-bold">
            <Paperclip className="w-3.5 h-3.5" />
            SOURCED EVIDENCE
          </span>
        );
      case "INFERRED":
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded border border-dashed border-purple-400 bg-purple-950/60 text-purple-300 text-xs font-mono font-bold">
            <Brain className="w-3.5 h-3.5" />
            INFERRED FACT
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded border-2 border-dotted border-rose-500 bg-rose-950/60 text-rose-300 text-xs font-mono font-bold">
            <AlertCircle className="w-3.5 h-3.5" />
            FLAGGED / AMBIGUOUS
          </span>
        );
    }
  };

  return (
    <AnimatePresence>
      {evidenceClauseId && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm">
          {/* Backdrop Click */}
          <div className="absolute inset-0" onClick={closeEvidence} />

          {/* Sliding Panel */}
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 220 }}
            className="relative w-full max-w-lg h-full bg-[#070b14] border-l border-cyan-500/30 p-6 flex flex-col justify-between shadow-2xl overflow-y-auto"
          >
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-jetbrains font-bold text-sm text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-500/30">
                      {clause.id}
                    </span>
                    <Badge variant="outline" className="text-xs font-mono border-slate-700 text-slate-300">
                      {clause.contractTitle}
                    </Badge>
                  </div>
                  <h3 className="font-orbitron font-bold text-lg text-white">
                    {clause.heading}
                  </h3>
                  <p className="text-xs text-slate-400 font-rajdhani uppercase tracking-wider">
                    {clause.section} • TYPE: {clause.type}
                  </p>
                </div>

                <button
                  onClick={closeEvidence}
                  className="p-1 rounded-lg border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Status Badges Row */}
              <div className="flex items-center gap-3 flex-wrap">
                {renderBadgeType()}

                <span
                  className={`text-xs font-mono px-2 py-0.5 rounded font-bold ${
                    clause.citationStatus === "EXACT"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-500/40"
                      : "bg-amber-950 text-amber-400 border border-amber-500/40"
                  }`}
                >
                  CITATION: {clause.citationStatus}
                </span>

                <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                  {clause.status}
                </span>
              </div>

              {/* Verbatim Clause Text with Quote Highlight */}
              <div className="space-y-2">
                <span className="text-xs font-rajdhani font-bold uppercase tracking-wider text-slate-400">
                  VERBATIM SOURCE TEXT
                </span>
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/80 text-xs font-mono text-slate-300 leading-relaxed whitespace-pre-wrap selection:bg-cyan-500/30">
                  {clause.highlightSnippet ? (
                    <>
                      {clause.text.split(clause.highlightSnippet)[0]}
                      <mark className="bg-amber-400/20 text-amber-300 px-1 py-0.5 rounded border border-amber-400/40 font-bold">
                        {clause.highlightSnippet}
                      </mark>
                      {clause.text.split(clause.highlightSnippet)[1]}
                    </>
                  ) : (
                    clause.text
                  )}
                </div>
              </div>

              {/* 65% Gate Score Breakdown */}
              <div className="space-y-3 p-4 rounded-xl border border-cyan-500/20 bg-slate-900/50">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-rajdhani font-bold uppercase tracking-wider text-cyan-300">
                    ODIN PROMOTION GATE (65% THRESHOLD)
                  </span>
                  <span className="font-jetbrains text-sm font-bold text-emerald-400">
                    {clause.scoreBreakdown.composite}% COMPOSITE
                  </span>
                </div>

                <div className="space-y-2 text-xs font-jetbrains">
                  {[
                    { label: "Exact Citation Match", val: clause.scoreBreakdown.citation },
                    { label: "Agent Reasoning Confidence", val: clause.scoreBreakdown.confidence },
                    { label: "Council Cross-Agreement", val: clause.scoreBreakdown.agreement },
                    { label: "External Ledger Verification", val: clause.scoreBreakdown.external },
                  ].map((metric) => (
                    <div key={metric.label}>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                        <span>{metric.label}</span>
                        <span className="text-slate-200">{metric.val}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          style={{ width: `${metric.val}%` }}
                          className={`h-full rounded-full ${
                            metric.val >= 65 ? "bg-cyan-400" : "bg-rose-500"
                          }`}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Provenance Trail */}
              <div className="space-y-2 p-3.5 rounded-lg border border-slate-800 bg-slate-950 text-xs font-mono text-slate-400">
                <span className="text-[10px] font-rajdhani uppercase tracking-wider text-slate-500 block">
                  PROVENANCE AUDIT TRAIL
                </span>
                <div className="flex justify-between">
                  <span>Extracted By:</span>
                  <span className="text-cyan-300 font-bold">{clause.provenance.extractedBy}</span>
                </div>
                <div className="flex justify-between">
                  <span>Timestamp:</span>
                  <span className="text-slate-200">{clause.provenance.timestamp}</span>
                </div>
                <div className="flex justify-between">
                  <span>Character Offset:</span>
                  <span className="text-slate-200">Byte {clause.provenance.docOffset}</span>
                </div>
                <div className="flex justify-between">
                  <span>SHA-256 Digest:</span>
                  <span className="text-slate-200 font-jetbrains">{clause.provenance.contentHash}...</span>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="pt-4 border-t border-slate-800 flex justify-end">
              <button
                onClick={closeEvidence}
                className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-rajdhani font-bold text-xs uppercase tracking-wider"
              >
                Close Drawer
              </button>
            </div>
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
}
