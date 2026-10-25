"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Layers,
  AlertTriangle,
  FileText,
  Shield,
  Eye,
  Zap,
  Filter,
  Maximize2,
  RefreshCw,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";

export function ContractGraphView() {
  const { contracts, edges, openEvidence, openDiff } = useOdinStore();
  const [filterConflictsOnly, setFilterConflictsOnly] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const filteredContracts = contracts.filter((c) => {
    if (filterConflictsOnly && c.conflictsCount === 0) return false;
    if (selectedCategory !== "ALL" && c.category !== selectedCategory) return false;
    return true;
  });

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case "upstream":
        return "border-cyan-500/50 bg-cyan-950/30 text-cyan-300";
      case "customer":
        return "border-emerald-500/50 bg-emerald-950/30 text-emerald-300";
      case "contractor":
        return "border-purple-500/50 bg-purple-950/30 text-purple-300";
      default:
        return "border-amber-500/50 bg-amber-950/30 text-amber-300";
    }
  };

  return (
    <div className="relative w-full h-full min-h-[580px] rounded-xl border border-cyan-500/20 bg-slate-950/60 p-5 flex flex-col justify-between overflow-hidden">
      {/* Top Filter Chips */}
      <div className="flex flex-wrap items-center justify-between gap-3 z-10 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span className="font-rajdhani font-bold text-xs uppercase tracking-wider text-slate-200">
            CONTRACT TOPOLOGY & CONFLICT GRAPH
          </span>
          <Badge variant="outline" className="text-[10px] font-mono border-slate-700 text-slate-400">
            {contracts.length} NODES • {edges.length} RELATIONS
          </Badge>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={() => setFilterConflictsOnly(!filterConflictsOnly)}
            className={`px-2.5 py-1 rounded text-xs font-rajdhani font-bold transition-all border ${
              filterConflictsOnly
                ? "border-rose-500 bg-rose-950/60 text-rose-300 shadow-sm shadow-rose-500/40"
                : "border-slate-800 bg-slate-900/40 text-slate-400 hover:text-white"
            }`}
          >
            ⚡ Conflicts Only ({edges.filter((e) => e.type === "conflicts_with").length})
          </button>

          {(["ALL", "upstream", "customer", "contractor"] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase transition-all border ${
                selectedCategory === cat
                  ? "border-cyan-400 bg-cyan-950/60 text-cyan-300"
                  : "border-slate-800 bg-slate-900/30 text-slate-400 hover:text-white"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Interactive Visual Graph Canvas */}
      <div className="relative flex-1 my-4 flex items-center justify-center min-h-[380px]">
        {/* Subtle grid background */}
        <div className="absolute inset-0 bg-hex-grid opacity-30 pointer-events-none" />

        {/* Graph Nodes Grid (High-Performance SVG + Interactive Node Cards) */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full z-10">
          {filteredContracts.map((contract) => (
            <motion.div
              key={contract.id}
              whileHover={{ scale: 1.02 }}
              onClick={() => openEvidence(`${contract.id}-S1`)}
              className={`p-3.5 rounded-xl border hud-panel transition-all cursor-pointer ${getCategoryColor(
                contract.category
              )}`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <span className="font-jetbrains font-black text-sm px-1.5 py-0.5 rounded bg-black/40 border border-white/10">
                    {contract.id}
                  </span>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                    {contract.category}
                  </span>
                </div>
                {contract.conflictsCount > 0 && (
                  <Badge variant="destructive" className="text-[9px] px-1 py-0 bg-rose-950 text-rose-400 border-rose-700 animate-pulse">
                    {contract.conflictsCount} Conflict{contract.conflictsCount > 1 ? "s" : ""}
                  </Badge>
                )}
              </div>

              <h4 className="font-rajdhani font-bold text-xs text-white leading-tight truncate mb-1">
                {contract.title}
              </h4>
              <p className="text-[10px] text-slate-400 truncate mb-2">
                Party: {contract.party}
              </p>

              <div className="flex items-center justify-between text-[10px] font-jetbrains border-t border-white/10 pt-2 text-slate-400">
                <span>{contract.clausesCount} Clauses</span>
                {contract.valueAnnual ? (
                  <span className="text-emerald-400 font-bold">${(contract.valueAnnual / 1000).toFixed(0)}k/yr</span>
                ) : (
                  <span className="text-slate-500">Framework</span>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Active Conflict Radar Edge Bar */}
      <div className="z-10 p-3.5 rounded-xl border border-rose-500/30 bg-rose-950/20 backdrop-blur-sm space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-rajdhani font-bold uppercase tracking-wider text-rose-300 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-rose-400 animate-pulse" />
            Active Conflicting Edges Detected (Click to Compare Clauses)
          </span>
          <span className="text-[10px] font-mono text-slate-400">
            Pulsing Red: Unreconciled Cross-Contract Liabilities
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {edges
            .filter((e) => e.type === "conflicts_with")
            .map((edge) => (
              <button
                key={edge.id}
                onClick={() => {
                  const conf = edge.id === "edge-conflict-sla" ? "CONF-01" : edge.id === "edge-conflict-notice" ? "CONF-02" : "CONF-03";
                  openDiff(conf);
                }}
                className="p-2.5 rounded-lg border border-rose-500/40 bg-slate-950 hover:bg-slate-900 text-left transition-all group flex flex-col justify-between"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono font-bold text-rose-400 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                    {edge.source} ↔ {edge.target}
                  </span>
                  <Badge variant="outline" className="text-[9px] border-rose-800 text-rose-400">
                    {edge.severity}
                  </Badge>
                </div>
                <p className="text-[11px] text-slate-300 line-clamp-1 group-hover:text-white">
                  {edge.label}
                </p>
                <span className="text-[9px] text-cyan-400 mt-1 font-mono group-hover:underline">
                  Launch Clause Diff →
                </span>
              </button>
            ))}
        </div>
      </div>

      {/* Graph Legend Bottom */}
      <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-3 border-t border-slate-800/60">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400" /> Upstream
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Customer
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-purple-400" /> Contractor
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Standard
          </span>
          <span className="flex items-center gap-1 text-rose-400 font-bold">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" /> Pulsing: Conflict
          </span>
        </div>
        <span>Double-click node to inspect text</span>
      </div>
    </div>
  );
}
