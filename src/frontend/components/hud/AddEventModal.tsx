"use client";

import React, { useState } from "react";
import { X, Eye, UploadCloud, CheckCircle2, RefreshCw, Zap } from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { toast } from "sonner";

export function AddEventModal() {
  const { isAddEventOpen, closeAddEvent, addEvent, contracts } = useOdinStore();

  const [date, setDate] = useState("2026-11-20");
  const [type, setType] = useState("outage");
  const [summary, setSummary] = useState("");
  const [contractId, setContractId] = useState("A1");
  const [isSimulating, setIsSimulating] = useState(false);

  if (!isAddEventOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!summary) return;

    setIsSimulating(true);

    // Simulate Heimdall event correlation
    setTimeout(() => {
      addEvent({
        date,
        type,
        summary,
        contractId,
      });
      setIsSimulating(false);
      toast.success("Event Mapped by Heimdall", {
        description: `Correlated with ${contractId} • Alert generated with +$15,000 exposure delta.`,
      });
    }, 900);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4">
      <div className="absolute inset-0" onClick={closeAddEvent} />

      <div className="relative w-full max-w-lg bg-[#070b14] border border-cyan-500/40 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-cyan-400" />
              <h3 className="font-orbitron font-bold text-base text-white">
                INGEST OPERATIONAL EVENT
              </h3>
            </div>
            <button
              type="button"
              onClick={closeAddEvent}
              className="p-1 rounded-lg border border-slate-800 text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-3 text-xs font-rajdhani">
            <div>
              <label className="block uppercase tracking-wider text-slate-400 mb-1 font-bold">
                Incident Date
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-jetbrains text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block uppercase tracking-wider text-slate-400 mb-1 font-bold">
                Event Category
              </label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-jetbrains text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="outage">Carrier / Infrastructure Outage</option>
                <option value="late_payment">Delayed Customer Settlement / Default</option>
                <option value="email">Formal Customer Dispute Letter</option>
                <option value="regulatory">Regulatory / Compliance Inquiry</option>
                <option value="other">General Operational Communication</option>
              </select>
            </div>

            <div>
              <label className="block uppercase tracking-wider text-slate-400 mb-1 font-bold">
                Impacted Contract Association
              </label>
              <select
                value={contractId}
                onChange={(e) => setContractId(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-jetbrains text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {contracts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.id} — {c.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block uppercase tracking-wider text-slate-400 mb-1 font-bold">
                Event Summary & Telemetry Details
              </label>
              <textarea
                rows={3}
                required
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="e.g. StratoNode secondary node latency spiked over 4,200ms; Harbor automated health probes failed 14 times..."
                className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Drag & drop .jsonl indicator */}
            <div className="p-3 rounded-lg border border-dashed border-slate-800 bg-slate-950/40 text-center text-slate-500 text-[11px] flex items-center justify-center gap-2">
              <UploadCloud className="w-4 h-4 text-cyan-400" />
              <span>Or drop an Odin events_drop.jsonl file here</span>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
            <button
              type="button"
              onClick={closeAddEvent}
              className="px-4 py-2 rounded-lg border border-slate-800 text-slate-400 hover:text-white text-xs font-bold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSimulating}
              className="px-5 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-rajdhani font-bold text-xs uppercase tracking-wider flex items-center gap-1.5"
            >
              {isSimulating ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Heimdall Mapping...
                </>
              ) : (
                <>
                  <Zap className="w-3.5 h-3.5" />
                  Correlate & Submit
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
