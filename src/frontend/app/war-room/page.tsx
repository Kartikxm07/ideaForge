"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Scale,
  DollarSign,
  AlertTriangle,
  FileText,
  Clock,
  Layers,
  ArrowUpRight,
  PlusCircle,
  ExternalLink,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { AddContractModal } from "@/components/hud/AddContractModal";

export default function MinimalDashboard() {
  const { nodes, timelineEvents } = useOdinStore();
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#FDFBF7] text-[#18181B] flex flex-col">
      {/* Streamlined Financial Navbar */}
      <header className="border-b border-black/[0.06] bg-white px-8 py-3.5 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#D4A017] flex items-center justify-center text-white">
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-sm tracking-tight">ODIN</span>
            <span className="ml-2 text-[11px] text-zinc-400 font-medium tracking-wide">
              FINANCIAL SOLUTIONS
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#D4A017] hover:bg-[#B8880E] text-white text-xs font-semibold shadow-sm transition-all"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Add Contract
          </button>
          <Link
            href="/onboarding"
            className="text-xs font-medium text-zinc-600 hover:text-zinc-900 px-3 py-1.5 rounded-lg border border-zinc-200 bg-zinc-50"
          >
            Entity Settings
          </Link>
          <Link
            href="/login"
            className="text-xs font-medium text-zinc-500 hover:text-zinc-800"
          >
            Sign Out
          </Link>
        </div>
      </header>

      {/* Main minimal dashboard content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8 space-y-6">
        {/* Title row */}
        <div className="flex items-baseline justify-between">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900">Portfolio Intelligence</h1>
            <p className="text-xs text-zinc-500 mt-1">
              Active liability radar and contract conflict synthesis.
            </p>
          </div>
        </div>

        {/* 3 Clean Key Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white p-5 rounded-xl border border-black/[0.07] shadow-sm">
            <div className="flex items-center justify-between text-zinc-500 text-xs font-semibold mb-2">
              <span>TOTAL FINANCIAL EXPOSURE</span>
              <DollarSign className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-bold font-mono text-zinc-900">$60,500</p>
            <p className="text-[11px] text-zinc-400 mt-1">Gross liabilities under review</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-black/[0.07] shadow-sm">
            <div className="flex items-center justify-between text-zinc-500 text-xs font-semibold mb-2">
              <span>UNRESOLVED CLAUSE CONFLICTS</span>
              <AlertTriangle className="w-4 h-4 text-amber-600" />
            </div>
            <p className="text-2xl font-bold font-mono text-amber-700">3 Conflicts</p>
            <p className="text-[11px] text-zinc-400 mt-1">1 Critical SLA · 2 High</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-black/[0.07] shadow-sm">
            <div className="flex items-center justify-between text-zinc-500 text-xs font-semibold mb-2">
              <span>ACTIVE AGREEMENTS</span>
              <FileText className="w-4 h-4 text-emerald-600" />
            </div>
            <p className="text-2xl font-bold font-mono text-zinc-900">{nodes.length} Documents</p>
            <p className="text-[11px] text-zinc-400 mt-1">Monitored across 8 counterparties</p>
          </div>
        </div>

        {/* Simplified Agreements & Deadlines Table */}
        <div className="bg-white border border-black/[0.07] rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-zinc-100 flex items-center justify-between">
            <h2 className="text-sm font-bold text-zinc-800">Monitored Contracts & Counterparties</h2>
            <span className="text-xs text-zinc-400">{nodes.length} contracts loaded</span>
          </div>

          <div className="divide-y divide-zinc-100">
            {nodes.slice(0, 6).map((node) => (
              <div key={node.id} className="px-6 py-3.5 flex items-center justify-between hover:bg-zinc-50/50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-600 font-semibold text-xs">
                    {node.id}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-zinc-900">{node.label}</p>
                    <p className="text-xs text-zinc-400">{node.counterparty}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {node.conflicts.length > 0 ? (
                    <span className="text-[11px] font-semibold text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                      {node.conflicts.length} conflict{node.conflicts.length > 1 ? "s" : ""}
                    </span>
                  ) : (
                    <span className="text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                      Compliant
                    </span>
                  )}
                  <span className="text-xs font-mono font-medium text-zinc-600">
                    {node.value ? `$${node.value.toLocaleString()}` : "—"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upcoming Action Milestones */}
        <div className="bg-white border border-black/[0.07] rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-bold text-zinc-800 mb-4">Upcoming Notice Deadlines</h2>
          <div className="space-y-3">
            {timelineEvents.slice(0, 3).map((event) => (
              <div key={event.id} className="flex items-center justify-between p-3.5 rounded-lg border border-zinc-100 bg-zinc-50/60 text-xs">
                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4 text-amber-700" />
                  <div>
                    <p className="font-semibold text-zinc-900">{event.title}</p>
                    <p className="text-[11px] text-zinc-500">{event.date} · {event.description}</p>
                  </div>
                </div>
                <span className="font-medium text-amber-900 bg-amber-100/70 px-2 py-0.5 rounded text-[10px]">
                  {event.type}
                </span>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Add contract modal */}
      <AddContractModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onAdd={(c) => console.log("Added contract:", c)}
      />

      <footer className="text-center py-4 text-xs text-zinc-400 border-t border-black/[0.04]">
        ODIN Platform · Institutional Financial Solutions
      </footer>
    </div>
  );
}
