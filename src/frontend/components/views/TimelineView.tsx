"use client";

import React from "react";
import { Clock, Calendar, Flag, DollarSign, AlertCircle } from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";

export function TimelineView() {
  const { swimlanes, currentDate, openEvidence } = useOdinStore();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between p-4 rounded-xl border border-cyan-500/20 bg-slate-950/60">
        <div>
          <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-purple-400" />
            CONTRACT OBLIGATION & EXPOSURE TIMELINE (GANTT SWIMLANES)
          </h3>
          <p className="text-xs text-slate-400 font-rajdhani uppercase tracking-wider">
            Renewal windows, notice cutoff flags, payment settlements, and cumulative risk trajectory
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-cyan-300 bg-cyan-950/60 px-3 py-1.5 rounded-lg border border-cyan-500/30">
          <span>NOW: {currentDate}</span>
        </div>
      </div>

      {/* Gantt Swimlanes Container */}
      <div className="hud-panel p-6 rounded-xl space-y-6 overflow-x-auto">
        {/* Months Bar */}
        <div className="grid grid-cols-9 gap-2 text-xs font-jetbrains font-bold text-slate-400 border-b border-slate-800 pb-2">
          <div className="col-span-2 text-slate-300">Contract Agreement</div>
          {["Aug '26", "Sep '26", "Oct '26", "Nov '26", "Dec '26", "Jan '27", "Feb '27"].map((m) => (
            <div key={m} className="text-center">{m}</div>
          ))}
        </div>

        {/* Swimlane Rows */}
        <div className="space-y-5">
          {swimlanes.map((lane) => (
            <div key={lane.contractId} className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-jetbrains font-bold text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/30">
                    {lane.contractId}
                  </span>
                  <span className="font-rajdhani font-bold text-white">{lane.contractTitle}</span>
                </div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                  <span className="flex items-center gap-1">
                    <Flag className="w-3 h-3 text-amber-400" /> Notice Cutoff: {lane.milestones.find((milestone) => milestone.type === "notice")?.date ?? "Not available"}
                  </span>
                </div>
              </div>

              {/* Progress bar container */}
              <div className="relative h-9 w-full bg-slate-900/60 border border-slate-800 rounded-lg flex items-center p-1">
                {/* Active Contract Term Bar */}
                <div className="h-full bg-gradient-to-r from-blue-900/50 via-cyan-900/50 to-indigo-900/50 border border-cyan-500/40 rounded flex items-center px-3 text-[11px] font-mono text-cyan-200 w-4/5">
                  Term: {lane.startDate} → {lane.endDate}
                </div>

                {/* Renewal Window Overlay */}
                <div className="absolute right-12 h-6 px-2 rounded bg-amber-500/20 border border-amber-400 text-[10px] font-mono text-amber-300 flex items-center">
                  Renewal Window
                </div>

                {/* Payment Events Dots */}
                {lane.milestones.filter((milestone) => milestone.type === "payment").map((pe, idx) => (
                  <div
                    key={idx}
                    title={`Sample scheduled payment: ${pe.amount == null ? "Amount unavailable" : "$" + pe.amount.toLocaleString("en-US")} on ${pe.date}`}
                    style={{ left: `${20 + idx * 18}%` }}
                    className="absolute w-3.5 h-3.5 rounded-full border-2 border-slate-400 bg-slate-800 flex items-center justify-center transform -translate-x-1/2"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400 pt-4 border-t border-slate-800">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Settled Payment
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Missed / Withheld
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded bg-amber-400" /> Renewal Window
            </span>
            <span className="flex items-center gap-1.5">
              <Flag className="w-3 h-3 text-amber-400" /> Mandatory Notice Cutoff
            </span>
          </div>
          <span>NOW timeline synchronized with Norns Temporal Engine</span>
        </div>
      </div>

      {/* Cumulative Risk Trajectory Curves: Best Case vs Worst Case */}
      <div className="hud-panel p-6 rounded-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h4 className="font-orbitron font-bold text-sm text-white">
              CUMULATIVE EXPOSURE TRAJECTORY (BEST VS WORST CASE)
            </h4>
            <p className="text-xs text-slate-400 font-rajdhani uppercase">
              Projected financial leakage if Tyr recommended notices are executed vs ignored
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="flex items-center gap-1 text-emerald-400 font-bold">
              ── Best Case ($24.5k final)
            </span>
            <span className="flex items-center gap-1 text-rose-400 font-bold">
              ── Worst Case ($128.4k final)
            </span>
          </div>
        </div>

        {/* ASCII / CSS Curve visualization */}
        <div className="h-44 w-full flex items-end justify-between gap-4 pt-4 px-2 font-jetbrains text-xs">
          {[
            { label: "Oct '26 (CP1)", best: 18.5, worst: 18.5 },
            { label: "Nov '26 (Drop 1)", best: 42.0, worst: 60.5 },
            { label: "Dec '26 (Cure)", best: 31.0, worst: 95.0 },
            { label: "Jan '27 (CP3)", best: 24.5, worst: 128.4 },
          ].map((pt) => (
            <div key={pt.label} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
              <div className="w-full flex items-end justify-center gap-3 h-32">
                {/* Best Case Bar */}
                <div
                  style={{ height: `${(pt.best / 140) * 100}%` }}
                  className="w-8 rounded-t bg-emerald-500/80 border border-emerald-400 flex items-start justify-center pt-1 text-[10px] text-slate-950 font-bold"
                >
                  ${pt.best}k
                </div>
                {/* Worst Case Bar */}
                <div
                  style={{ height: `${(pt.worst / 140) * 100}%` }}
                  className="w-8 rounded-t bg-rose-500/80 border border-rose-400 flex items-start justify-center pt-1 text-[10px] text-slate-950 font-bold"
                >
                  ${pt.worst}k
                </div>
              </div>
              <span className="text-[11px] text-slate-400">{pt.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
