"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { HudHeader } from "@/components/hud/HudHeader";
import {
  Cpu,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Play,
  ArrowRight,
  Shield,
  Zap,
  Layers,
  Terminal,
  Activity,
  DollarSign,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function AnalysisPage() {
  const router = useRouter();
  const [activeStage, setActiveStage] = useState(4);
  const [llmCallCount, setLlmCallCount] = useState(14);
  const [spentBudget, setSpentBudget] = useState(14.20);

  const agents = [
    { name: "Odin", role: "Orchestrator", color: "text-amber-400", ring: "stroke-amber-400", progress: 100, status: "ROUTING" },
    { name: "Thor", role: "Extractor", color: "text-cyan-400", ring: "stroke-cyan-400", progress: 100, status: "INDEXED" },
    { name: "Norns", role: "Timekeeper", color: "text-emerald-400", ring: "stroke-emerald-400", progress: 100, status: "CALIBRATED" },
    { name: "Loki", role: "Challenger", color: "text-purple-400", ring: "stroke-purple-400", progress: 95, status: "ATTACKING" },
    { name: "Heimdall", role: "Watcher", color: "text-teal-400", ring: "stroke-teal-400", progress: 90, status: "MONITORING" },
    { name: "Tyr", role: "Arbiter", color: "text-rose-400", ring: "stroke-rose-400", progress: 85, status: "RULING" },
  ];

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 bg-hex-grid flex flex-col">
      <HudHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto p-6 space-y-6">
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-4">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-400 block">
              REAL-TIME AGENT COUNCIL TELEMETRY
            </span>
            <h1 className="font-orbitron font-bold text-2xl text-white">
              LIVE AGENT OPS — CONTRACT ANALYSIS IN PROGRESS
            </h1>
          </div>

          <Link href="/war-room">
            <Button className="bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs tracking-wider px-5 shadow-lg shadow-amber-600/20">
              View Intelligence Dashboard <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          </Link>
        </div>

        {/* Live Counters Banner */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="hud-panel p-4 rounded-xl space-y-1">
            <span className="text-xs font-rajdhani text-slate-400 uppercase font-bold">Execution Rounds</span>
            <div className="font-jetbrains text-2xl font-bold text-cyan-300">Round 3 / 3</div>
            <span className="text-[10px] text-slate-500 font-mono">Bounded convergence</span>
          </div>

          <div className="hud-panel p-4 rounded-xl space-y-1">
            <span className="text-xs font-rajdhani text-slate-400 uppercase font-bold">Inference Calls</span>
            <div className="font-jetbrains text-2xl font-bold text-emerald-300">{llmCallCount} Calls</div>
            <span className="text-[10px] text-slate-500 font-mono">100% Localhost Model</span>
          </div>

          <div className="hud-panel p-4 rounded-xl space-y-1">
            <span className="text-xs font-rajdhani text-slate-400 uppercase font-bold">Budget Expended</span>
            <div className="font-jetbrains text-2xl font-bold text-amber-300">${spentBudget.toFixed(2)}</div>
            <span className="text-[10px] text-slate-500 font-mono">Allowance: $50.00 Max</span>
          </div>

          <div className="hud-panel p-4 rounded-xl space-y-1">
            <span className="text-xs font-rajdhani text-slate-400 uppercase font-bold">Disputes Adjudicated</span>
            <div className="font-jetbrains text-2xl font-bold text-rose-300">3 Rulings</div>
            <span className="text-[10px] text-slate-500 font-mono">Tyr Traceable Rationale</span>
          </div>
        </div>

        {/* Per-Agent Progress Rings Grid */}
        <div className="hud-panel p-6 rounded-2xl space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-cyan-400" />
              Autonomous Agent Council Status
            </h3>
            <span className="text-xs font-mono text-cyan-400 animate-pulse">
              ● All Agents Active on SQLite State
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {agents.map((ag) => (
              <div
                key={ag.name}
                className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 flex flex-col items-center text-center space-y-3"
              >
                {/* SVG Progress Ring */}
                <div className="relative w-16 h-16 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="32"
                      cy="32"
                      r="26"
                      stroke="currentColor"
                      strokeWidth="4"
                      className="text-slate-800"
                      fill="transparent"
                    />
                    <circle
                      cx="32"
                      cy="32"
                      r="26"
                      stroke="currentColor"
                      strokeWidth="4"
                      strokeDasharray="163"
                      strokeDashoffset={163 - (163 * ag.progress) / 100}
                      className={ag.ring}
                      fill="transparent"
                    />
                  </svg>
                  <span className={`absolute font-jetbrains font-bold text-xs ${ag.color}`}>
                    {ag.progress}%
                  </span>
                </div>

                <div>
                  <h4 className="font-bold text-sm text-white font-rajdhani uppercase">{ag.name}</h4>
                  <p className="text-[10px] text-slate-400">{ag.role}</p>
                </div>

                <Badge variant="outline" className="text-[9px] font-mono border-slate-800 text-slate-300">
                  {ag.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        {/* Animated Agent-to-Agent Transition Map */}
        <div className="hud-panel p-6 rounded-2xl space-y-4">
          <h3 className="font-orbitron font-bold text-sm text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            Execution Workflow Sequence
          </h3>

          <div className="flex items-center justify-between gap-2 overflow-x-auto p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono">
            {[
              { name: "Thor", desc: "Facts & Spans" },
              { name: "Norns", desc: "Clock & Ledger" },
              { name: "Loki", desc: "Loopholes" },
              { name: "Thor", desc: "Clarify Q&A" },
              { name: "Heimdall", desc: "Event Verify" },
              { name: "Tyr", desc: "Ruling & Action" },
            ].map((step, idx) => (
              <React.Fragment key={idx}>
                <div className="p-3 rounded-lg border border-cyan-500/30 bg-slate-900/60 text-center shrink-0 min-w-28">
                  <span className="font-bold text-cyan-300 block">{step.name}</span>
                  <span className="text-[10px] text-slate-400">{step.desc}</span>
                </div>
                {idx < 5 && <ArrowRight className="w-4 h-4 text-slate-600 shrink-0" />}
              </React.Fragment>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
