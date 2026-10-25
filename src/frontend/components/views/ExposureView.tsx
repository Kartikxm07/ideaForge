"use client";

import React, { useState } from "react";
import {
  DollarSign,
  Scale,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  Layers,
  ArrowDownRight,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";

export function ExposureView() {
  const {
    currentSnapshot,
    exposureMode,
    setExposureMode,
    heatmapMode,
    setHeatmapMode,
    heatmap,
    openDiff,
  } = useOdinStore();

  const [selectedHeatmapCell, setSelectedHeatmapCell] = useState<{
    row: string;
    col: string;
    value: number;
    findingIds: string[];
  } | null>(null);

  // Calculations for Waterfall
  const grossLiability = exposureMode === "worst-case" ? 128450 : 88500;
  const upstreamRecovery = 3000;
  const insuranceBuffer = exposureMode === "worst-case" ? 40000 : 43500;
  const netUncovered = grossLiability - upstreamRecovery - insuranceBuffer;

  // Semicircular Gauge progress (0 to 100k exposure scale)
  const maxScale = 150000;
  const gaugePercent = Math.min(100, (currentSnapshot.totalExposure / maxScale) * 100);

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-cyan-500/20 bg-slate-950/60">
        <div>
          <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-amber-400" />
            FINANCIAL RISK RADAR & EXPOSURE WATERFALL
          </h3>
          <p className="text-xs text-slate-400 font-rajdhani uppercase tracking-wider">
            Simulated portfolio breach liability vs upstream indemnities and insurance limits
          </p>
        </div>

        {/* Expected vs Worst-Case Toggle */}
        <div className="flex items-center rounded-lg border border-slate-800 bg-slate-900/80 p-1">
          <button
            onClick={() => setExposureMode("expected")}
            className={`px-3 py-1 rounded text-xs font-rajdhani font-bold uppercase transition-all ${
              exposureMode === "expected"
                ? "bg-cyan-500 text-slate-950 shadow-sm shadow-cyan-500/50"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Expected Case ($60.5k)
          </button>
          <button
            onClick={() => setExposureMode("worst-case")}
            className={`px-3 py-1 rounded text-xs font-rajdhani font-bold uppercase transition-all ${
              exposureMode === "worst-case"
                ? "bg-rose-500 text-slate-950 shadow-sm shadow-rose-500/50"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Worst-Case Stress ($128.4k)
          </button>
        </div>
      </div>

      {/* Semicircular Gauge + Waterfall Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Glowing Semicircular Gauge */}
        <div className="hud-panel p-6 rounded-xl flex flex-col items-center justify-between text-center relative overflow-hidden">
          <span className="font-rajdhani text-xs font-bold uppercase tracking-wider text-slate-400">
            TOTAL EXPOSURE GAUGE (VS $500K POLICY)
          </span>

          {/* Semicircular Graphic */}
          <div className="relative w-64 h-32 my-4 flex items-end justify-center overflow-hidden">
            <div className="absolute inset-0 w-64 h-64 rounded-full border-[18px] border-slate-800 border-b-transparent border-l-transparent transform -rotate-45" />
            {/* Colored Gauge Ring */}
            <div
              style={{
                background: `conic-gradient(from 180deg at 50% 100%, #10b981 0deg, #f59e0b 90deg, #ef4444 180deg)`,
                clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%)",
              }}
              className="absolute inset-0 w-64 h-32 opacity-80"
            />
            {/* Center Cutout */}
            <div className="absolute bottom-0 w-44 h-22 bg-[#070b14] rounded-t-full flex flex-col items-center justify-end pb-2">
              <span className="font-jetbrains text-3xl font-black text-rose-400">
                ${(currentSnapshot.totalExposure / 1000).toFixed(1)}k
              </span>
              <span className="text-[10px] font-mono text-slate-400">PORTFOLIO DEFICIT</span>
            </div>
          </div>

          <div className="w-full flex items-center justify-between text-[11px] font-mono border-t border-slate-800 pt-3 text-slate-400">
            <span className="text-emerald-400">$0k (Safe)</span>
            <span className="text-amber-400">$75k (Alert)</span>
            <span className="text-rose-400">$150k+ (Breached)</span>
          </div>
        </div>

        {/* Right: Waterfall Decomposition Chart */}
        <div className="lg:col-span-2 hud-panel p-6 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-rajdhani text-xs font-bold uppercase tracking-wider text-cyan-300">
              WATERFALL DECOMPOSITION: GROSS LIABILITIES → UNCOVERED GAP
            </span>
            <Badge variant="outline" className="text-xs font-mono border-slate-700 text-slate-400">
              AUDITED BALANCE
            </Badge>
          </div>

          <div className="space-y-3 font-jetbrains text-xs">
            {/* Step 1: Gross Downstream Liabilities */}
            <div className="p-3 rounded-lg border border-rose-500/40 bg-rose-950/20 flex items-center justify-between">
              <div>
                <span className="font-bold text-rose-300 block">1. Gross Downstream Liabilities (Harbor + FleetFlow)</span>
                <span className="text-[11px] text-slate-400">Contractual liquidated damages & withholdings</span>
              </div>
              <span className="text-base font-bold text-rose-400" suppressHydrationWarning>+${grossLiability.toLocaleString("en-US")}</span>
            </div>

            {/* Step 2: Upstream Carrier Recovery Offset */}
            <div className="p-3 rounded-lg border border-cyan-500/40 bg-cyan-950/20 flex items-center justify-between">
              <div>
                <span className="font-bold text-cyan-300 block">2. Upstream StratoNode Service Credit Cap</span>
                <span className="text-[11px] text-slate-400">15% Monthly hosting cap under A2 §4.2</span>
              </div>
              <span className="text-base font-bold text-cyan-400" suppressHydrationWarning>-${upstreamRecovery.toLocaleString("en-US")}</span>
            </div>

            {/* Step 3: Insurance Policy Coverage Allowance */}
            <div className="p-3 rounded-lg border border-purple-500/40 bg-purple-950/20 flex items-center justify-between">
              <div>
                <span className="font-bold text-purple-300 block">3. Chubb Cyber Shield Policy Allocation</span>
                <span className="text-[11px] text-slate-400">Policy CH-CYB-2026-99 deductible offset</span>
              </div>
              <span className="text-base font-bold text-purple-400" suppressHydrationWarning>-${insuranceBuffer.toLocaleString("en-US")}</span>
            </div>

            {/* Result: Net Uncovered Exposure */}
            <div className="p-4 rounded-xl border-2 border-amber-500/60 bg-amber-950/30 flex items-center justify-between">
              <div>
                <span className="font-bold text-sm text-amber-300 block">NET UNCOVERED BALANCE (CAPITAL AT RISK)</span>
                <span className="text-[11px] text-slate-400">Must be addressed via Tyr formal dispute notices</span>
              </div>
              <span className="text-xl font-black text-amber-400" suppressHydrationWarning>${netUncovered.toLocaleString("en-US")}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Heatmap Section (3 Modes) */}
      <div className="hud-panel p-6 rounded-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span className="font-rajdhani font-bold text-xs uppercase tracking-wider text-slate-200">
              CROSS-PORTFOLIO RISK HEATMAP MATRIX
            </span>
          </div>

          {/* 3 Modes Selector */}
          <div className="flex items-center rounded-lg border border-slate-800 bg-slate-900/80 p-0.5 text-xs">
            {[
              { id: "contract-month" as const, label: "Contract × Month" },
              { id: "clause-month" as const, label: "Clause Type × Month" },
              { id: "contract-clause" as const, label: "Contract × Clause Type" },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => setHeatmapMode(m.id)}
                className={`px-3 py-1 rounded text-xs font-rajdhani font-bold uppercase transition-all ${
                  heatmapMode === m.id
                    ? "bg-cyan-500 text-slate-950 shadow-sm shadow-cyan-500/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* Heatmap Grid */}
        <div className="grid grid-cols-5 gap-2 text-xs font-jetbrains">
          {/* Header Row */}
          <div className="text-slate-500 font-bold p-2">Entity \ Period</div>
          {["2026-10 (CP1)", "2026-11 (Drop 1)", "2026-12", "2027-01 (CP3)"].map((col) => (
            <div key={col} className="text-slate-400 font-bold p-2 text-center border-b border-slate-800">
              {col}
            </div>
          ))}

          {/* Heatmap Rows */}
          {["StratoNode A1/A2", "Harbor Retail B1", "FleetFlow C1", "Apex Systems D1"].map((rowName) => (
            <React.Fragment key={rowName}>
              <div className="text-slate-300 font-bold p-2 flex items-center bg-slate-900/30 rounded">
                {rowName}
              </div>
              {["2026-10", "2026-11", "2026-12", "2027-01"].map((colName) => {
                const cell = heatmap.find((c) => c.row === rowName && c.col === colName);
                const val = cell?.value || 0;

                const getCellColor = (v: number) => {
                  if (v >= 80) return "bg-rose-950/80 border-rose-500 text-rose-300 shadow-sm shadow-rose-500/40";
                  if (v >= 50) return "bg-amber-950/80 border-amber-500 text-amber-300";
                  if (v >= 20) return "bg-yellow-950/60 border-yellow-500 text-yellow-300";
                  return "bg-slate-900/40 border-slate-800 text-slate-500";
                };

                return (
                  <button
                    key={`${rowName}-${colName}`}
                    onClick={() => {
                      if (cell) {
                        setSelectedHeatmapCell(cell);
                        if (cell.findingIds.length > 0) {
                          openDiff(cell.findingIds[0]);
                        }
                      }
                    }}
                    className={`p-3 rounded-lg border text-center font-bold transition-all hover:scale-105 ${getCellColor(
                      val
                    )}`}
                  >
                    <div>{val}%</div>
                    {cell && cell.findingIds.length > 0 && (
                      <div className="text-[9px] uppercase font-mono mt-0.5 opacity-80">
                        {cell.findingIds.length} Issue{cell.findingIds.length > 1 ? "s" : ""}
                      </div>
                    )}
                  </button>
                );
              })}
            </React.Fragment>
          ))}
        </div>

        <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-800">
          <span>Click any cell to inspect correlating findings and clause diffs</span>
          <div className="flex items-center gap-3">
            <span className="text-slate-500">&lt;20% Low</span>
            <span className="text-yellow-400">20-50% Moderate</span>
            <span className="text-amber-400">50-80% Elevated</span>
            <span className="text-rose-400 font-bold">80%+ Critical</span>
          </div>
        </div>
      </div>
    </div>
  );
}
