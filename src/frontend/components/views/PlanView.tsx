"use client";

import React from "react";
import { Cpu, CheckCircle2, RefreshCw, AlertTriangle, Layers, ArrowRight } from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";

export function PlanView() {
  const { contracts } = useOdinStore();

  const planRows = [
    { target: "STD", title: "Master Standard Terms", workstream: "Precedence Hierarchy & Notice Baseline", agent: "Odin / Thor", status: "COMPLETE", progress: 100 },
    { target: "A1", title: "Cloud Hosting Agreement", workstream: "Base Liability Caps & Term Expirations", agent: "Thor", status: "COMPLETE", progress: 100 },
    { target: "A2", title: "StratoNode SLA", workstream: "Service Credit Remedy Exclusivity Extraction", agent: "Thor / Loki", status: "COMPLETE", progress: 100 },
    { target: "A3", title: "StratoNode SLA Amendment", workstream: "Cure Window Supersession Verification", agent: "Loki / Tyr", status: "FLAGGED", progress: 92 },
    { target: "B1", title: "Harbor Retail Route Agreement", workstream: "Downstream Penalty & Liquidated Damages", agent: "Thor / Norns", status: "COMPLETE", progress: 100 },
    { target: "B2", title: "Harbor Security Addendum", workstream: "Clean-Room IP Exclusivity Verification", agent: "Thor / Heimdall", status: "COMPLETE", progress: 100 },
    { target: "C1", title: "FleetFlow Commercial Agreement", workstream: "Fuel Benchmark Indexation Stress Test", agent: "Norns", status: "COMPLETE", progress: 100 },
    { target: "D1", title: "Apex Contractor Agreement", workstream: "Background Heuristics Rights Carveout", agent: "Thor / Loki", status: "FLAGGED", progress: 88 },
    { target: "CROSS", title: "Cross-Contract Synthesis", workstream: "Asymmetric Recovery Gap & Sovereign Adjudication", agent: "Odin / Tyr", status: "ACTIVE", progress: 85 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between p-4 rounded-xl border border-cyan-500/20 bg-slate-950/60">
        <div>
          <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
            <Cpu className="w-5 h-5 text-amber-400" />
            ODIN MASTER WORKSTREAM PLAN (PER-CONTRACT + CROSS)
          </h3>
          <p className="text-xs text-slate-400 font-rajdhani uppercase tracking-wider">
            Autonomous execution roadmap, agent assignment matrices, and reconciliation milestones
          </p>
        </div>
        <Badge className="bg-cyan-950 text-cyan-300 border-cyan-600 font-mono text-xs">
          9 WORKSTREAMS ORCHESTRATED
        </Badge>
      </div>

      <div className="hud-panel p-6 rounded-xl space-y-3">
        <div className="grid grid-cols-12 gap-3 text-xs font-jetbrains font-bold text-slate-400 border-b border-slate-800 pb-2">
          <div className="col-span-2">Contract Target</div>
          <div className="col-span-3">Agreement Scope</div>
          <div className="col-span-4">Workstream Focus</div>
          <div className="col-span-2">Assigned Council</div>
          <div className="col-span-1 text-right">Status</div>
        </div>

        <div className="space-y-2.5">
          {planRows.map((row) => (
            <div
              key={row.target}
              className="grid grid-cols-12 gap-3 items-center p-3 rounded-lg border border-slate-800/80 bg-slate-900/40 hover:border-slate-700 text-xs font-jetbrains"
            >
              <div className="col-span-2 flex items-center gap-1.5 font-bold">
                <span className={`px-2 py-0.5 rounded text-[11px] ${
                  row.target === "CROSS" ? "bg-amber-400 text-slate-950 font-black" : "bg-cyan-950 text-cyan-300 border border-cyan-800"
                }`}>
                  {row.target}
                </span>
              </div>
              <div className="col-span-3 font-semibold text-white truncate">
                {row.title}
              </div>
              <div className="col-span-4 text-slate-300 text-[11px]">
                {row.workstream}
              </div>
              <div className="col-span-2 text-cyan-400 font-mono text-[11px]">
                {row.agent}
              </div>
              <div className="col-span-1 text-right">
                <Badge
                  className={`text-[9px] py-0 font-mono ${
                    row.status === "COMPLETE"
                      ? "bg-emerald-950 text-emerald-400 border-emerald-700"
                      : row.status === "FLAGGED"
                      ? "bg-rose-950 text-rose-400 border-rose-700"
                      : "bg-cyan-950 text-cyan-300 border-cyan-700 animate-pulse"
                  }`}
                >
                  {row.status}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
