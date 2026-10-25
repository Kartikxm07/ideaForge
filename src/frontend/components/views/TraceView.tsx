"use client";

import React from "react";
import {
  Terminal,
  Cpu,
  Layers,
  Database,
  ShieldCheck,
  CheckCircle2,
  AlertOctagon,
  Clock,
  ArrowRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function TraceView() {
  const transitions = [
    { from: "Ingestion", to: "Odin", event: "Manifest & Text Verification", status: "COMPLETE", time: "0.2s" },
    { from: "Odin", to: "Thor", event: "Clause Hierarchy Extraction", status: "COMPLETE", time: "1.4s" },
    { from: "Thor", to: "Norns", event: "Simulated Timeline & Ledger Match", status: "COMPLETE", time: "0.8s" },
    { from: "Norns", to: "Loki", event: "Adversarial Stress Testing", status: "COMPLETE", time: "2.1s" },
    { from: "Loki", to: "Thor", event: "Targeted Clarification (Round 1 & 2)", status: "RESOLVED", time: "1.1s" },
    { from: "Loki", to: "Heimdall", event: "Event & Outage Correlation", status: "VERIFIED", time: "0.9s" },
    { from: "Heimdall", to: "Tyr", event: "Dispute Adjudication & Notice Drafts", status: "COMPLETE", time: "1.6s" },
  ];

  const llmCalls = [
    { agent: "Thor", model: "llama3.2:local", tokens: 1840, latency: "820ms", cache: "HIT", retries: 0 },
    { agent: "Norns", model: "deterministic:py", tokens: 0, latency: "42ms", cache: "N/A", retries: 0 },
    { agent: "Loki", model: "llama3.2:local", tokens: 2150, latency: "1140ms", cache: "MISS", retries: 0 },
    { agent: "Heimdall", model: "deterministic:event_map", tokens: 0, latency: "65ms", cache: "N/A", retries: 0 },
    { agent: "Tyr", model: "llama3.2:local", tokens: 1420, latency: "790ms", cache: "HIT", retries: 0 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between p-4 rounded-xl border border-cyan-500/20 bg-slate-950/60">
        <div>
          <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
            <Terminal className="w-5 h-5 text-cyan-400" />
            AGENT TRANSITION SEQUENCE & DATA HYGIENE TRACE
          </h3>
          <p className="text-xs text-slate-400 font-rajdhani uppercase tracking-wider">
            Deterministic state checkpoints, LLM token consumption, latency budgets, and quarantine logs
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 bg-emerald-950/60 px-3 py-1.5 rounded-lg border border-emerald-500/30">
          <ShieldCheck className="w-4 h-4" />
          <span>ZERO PRIVACY LEAKS: LOCALHOST ONLY</span>
        </div>
      </div>

      {/* Agent Workflow Sequence */}
      <div className="hud-panel p-6 rounded-xl space-y-4">
        <span className="font-rajdhani text-xs font-bold uppercase tracking-wider text-cyan-300 block border-b border-slate-800 pb-2">
          STATEFUL WORKSTREAM SEQUENCE (BOUNDED EXECUTION)
        </span>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
          {transitions.map((t, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg border border-slate-800 bg-slate-900/50 space-y-1.5 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-cyan-400 font-bold">
                  {t.from} → {t.to}
                </span>
                <span className="text-[10px] text-slate-500">{t.time}</span>
              </div>
              <p className="text-slate-300 text-[11px]">{t.event}</p>
              <div className="flex items-center justify-between pt-1 border-t border-slate-800/80">
                <Badge className="bg-emerald-950 text-emerald-400 border-emerald-600 text-[9px] py-0">
                  {t.status}
                </Badge>
                <span className="text-[10px] text-slate-500">Step {idx + 1}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* LLM Inference Telemetry & Token Budget */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 hud-panel p-6 rounded-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="font-rajdhani text-xs font-bold uppercase tracking-wider text-cyan-300">
              INFERENCE AUDIT (LOCAL LLM + DETERMINISTIC AGENTS)
            </span>
            <span className="text-xs font-mono text-slate-400">Total Tokens: 5,410</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-jetbrains text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="pb-2">Agent</th>
                  <th className="pb-2">Model Engine</th>
                  <th className="pb-2">Tokens</th>
                  <th className="pb-2">Latency</th>
                  <th className="pb-2">Cache</th>
                  <th className="pb-2">Retries</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {llmCalls.map((c, i) => (
                  <tr key={i} className="hover:bg-slate-900/30">
                    <td className="py-2.5 font-bold text-white">{c.agent}</td>
                    <td className="py-2.5 text-cyan-400 text-[11px]">{c.model}</td>
                    <td className="py-2.5 text-slate-300">{c.tokens}</td>
                    <td className="py-2.5 text-slate-400">{c.latency}</td>
                    <td className="py-2.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        c.cache === "HIT" ? "bg-emerald-950 text-emerald-400" : "bg-slate-900 text-slate-400"
                      }`}>
                        {c.cache}
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-400">{c.retries}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Data Hygiene & Quarantine Panel */}
        <div className="hud-panel p-6 rounded-xl space-y-4">
          <span className="font-rajdhani text-xs font-bold uppercase tracking-wider text-rose-300 block border-b border-slate-800 pb-2">
            DATA HYGIENE & QUARANTINE LOG
          </span>

          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-1">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-200">Duplicate Ledger Entries</span>
                <Badge className="bg-emerald-950 text-emerald-400 border-emerald-600 text-[10px]">0 DUPES</Badge>
              </div>
              <p className="text-[10px] text-slate-500">payments_ledger.csv verified with zero duplicate hashes.</p>
            </div>

            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-1">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-200">Quarantined Events</span>
                <Badge className="bg-amber-950 text-amber-400 border-amber-600 text-[10px]">4 FILTERED</Badge>
              </div>
              <p className="text-[10px] text-slate-500">Marketing flyers & duplicate webhooks isolated from analysis.</p>
            </div>

            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-1">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-200">SHA-256 Hash Tamper Check</span>
                <Badge className="bg-emerald-950 text-emerald-400 border-emerald-600 text-[10px]">PASSED</Badge>
              </div>
              <p className="text-[10px] text-slate-500">All 8 contract files match bundle manifest hashes 100%.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
