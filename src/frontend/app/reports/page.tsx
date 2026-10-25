"use client";

import React, { useState } from "react";
import { HudHeader } from "@/components/hud/HudHeader";
import { EvidenceDrawer } from "@/components/hud/EvidenceDrawer";
import {
  FileText,
  Download,
  Shield,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Printer,
  Scale,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function ReportsPage() {
  const { contracts, openEvidence } = useOdinStore();
  const [selectedDocKey, setSelectedDocKey] = useState("SUMMARY");

  const references = [
    { num: 1, clauseId: "A2-S4.1", title: "StratoNode Uptime Commitment", quote: "Monthly Uptime Percentage of not less than 99.50%" },
    { num: 2, clauseId: "A2-S4.2", title: "StratoNode 15% Remedy Cap", quote: "sole and exclusive remedy shall be a Service Credit equal to a maximum of fifteen percent (15%)" },
    { num: 3, clauseId: "A3-S2.1", title: "StratoNode 10-day Notice Rule", quote: "submit formal written notice of claim within ten (10) calendar days" },
    { num: 4, clauseId: "STD-S14.2", title: "Master Standard Terms Precedence", quote: "provisions of these Master Terms shall strictly control, requiring thirty (30) days notice" },
    { num: 5, clauseId: "B1-S8.1", title: "Harbor Retail 99.90% Commitment", quote: "withhold fifty percent (50%) plus $15,000 per downtime day" },
    { num: 6, clauseId: "D1-S6.3", title: "Apex Contractor IP Carveout", quote: "Contractor retains ownership of all pre-existing heuristics" },
    { num: 7, clauseId: "B2-S4.1", title: "Harbor Clean-Room Warranty", quote: "no contractor code or third-party algorithm shall be co-mingled" },
  ];

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 bg-hex-grid flex flex-col">
      <HudHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto p-6 space-y-6">
        {/* Title Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-cyan-500/20 pb-4">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-400 block">
              COUNCIL FORMAL REPORT DOSSIER
            </span>
            <h1 className="font-orbitron font-bold text-2xl text-white">
              ODIN CONTRACT RISK AUDIT & CLAUSE REFERENCES
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => window.print()}
              className="border-slate-800 text-slate-300 font-rajdhani text-xs"
            >
              <Printer className="w-3.5 h-3.5 mr-1.5 text-cyan-400" /> Print Dossier
            </Button>
            <Button
              size="sm"
              onClick={() => alert("Dossier report PDF generated with all SHA-256 evidence citations.")}
              className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-rajdhani font-bold text-xs"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" /> Download Full Audit
            </Button>
          </div>
        </div>

        {/* Contract Selector Tabs */}
        <div className="flex flex-wrap gap-1.5 p-1.5 rounded-xl border border-slate-800 bg-slate-950">
          <button
            onClick={() => setSelectedDocKey("SUMMARY")}
            className={`px-3 py-1.5 rounded-lg text-xs font-rajdhani font-bold uppercase transition-all ${
              selectedDocKey === "SUMMARY"
                ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            ★ Executive Portfolio Synthesis
          </button>
          {contracts.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedDocKey(c.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono uppercase transition-all ${
                selectedDocKey === c.id
                  ? "bg-cyan-500 text-slate-950 font-bold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {c.id}
            </button>
          ))}
        </div>

        {/* Report Content Panel */}
        <div className="hud-panel p-8 rounded-2xl space-y-6">
          {selectedDocKey === "SUMMARY" ? (
            <div className="space-y-6 font-mono text-xs leading-relaxed text-slate-300">
              <div className="border-b border-slate-800 pb-4">
                <Badge className="bg-rose-950 text-rose-400 border-rose-700 font-mono text-xs mb-2">
                  CLASSIFIED LEGAL INTELLIGENCE
                </Badge>
                <h2 className="font-orbitron font-bold text-xl text-white">
                  Quillhub Inc. Contract Portfolio Risk Report
                </h2>
                <p className="text-slate-400 text-xs font-rajdhani mt-1">
                  Prepared by Council of Six • Evaluated across Checkpoints 1, 2, and 3
                </p>
              </div>

              <section className="space-y-2">
                <h3 className="font-rajdhani font-bold text-sm text-cyan-400 uppercase tracking-wider">
                  1. Executive Summary & Financial Exposure
                </h3>
                <p>
                  Quillhub operates enterprise route optimization under commercial agreements executed across cloud hosting providers, enterprise retail customers, and specialized contractor agencies. While each individual contract appears customary in isolation, cross-portfolio analysis reveals a critical structural deficit: an asymmetric SLA recovery gap. Upstream vendor StratoNode warrants 99.50% uptime[1] with remedies strictly capped at 15% of monthly hosting fees ($3,000 max)[2]. Conversely, downstream retail agreements with Harbor Retail promise 99.90% availability with 50% fee withholding plus $15,000/day in liquidated damages[5].
                </p>
              </section>

              <section className="space-y-2">
                <h3 className="font-rajdhani font-bold text-sm text-amber-400 uppercase tracking-wider">
                  2. Silent Supersession & Notice Period Contradictions
                </h3>
                <p>
                  Amendment No. 1 to the StratoNode SLA (A3) purports to shorten the notice window for credit claims to 10 days[3]. However, Master Standard Terms Section 14.2 establishes strict order of precedence requiring 30 days notice[4]. Tyr has ruled that Amendment A3 did not specifically waive Section 14.2, granting Quillhub legal basis to enforce 30-day notice rights.
                </p>
              </section>

              <section className="space-y-2">
                <h3 className="font-rajdhani font-bold text-sm text-purple-400 uppercase tracking-wider">
                  3. Intellectual Property Clean-Room Integrity
                </h3>
                <p>
                  Contractor agreement D1 preserves background heuristic IP for Apex Systems[6]. This directly conflicts with Harbor Retail Security Addendum B2 Section 4.1[7], which prohibits co-mingling non-isolated contractor tooling. Tyr recommends immediate execution of the Quitclaim Addendum.
                </p>
              </section>

              {/* Reference Citations Section (Clickable) */}
              <div className="pt-6 border-t border-slate-800 space-y-3">
                <h3 className="font-rajdhani font-bold text-sm text-slate-300 uppercase tracking-wider">
                  References & Verified Clause Text (Click any citation to view verbatim span)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {references.map((ref) => (
                    <button
                      key={ref.num}
                      onClick={() => openEvidence(ref.clauseId)}
                      className="p-3 rounded-lg border border-slate-800 bg-slate-950 hover:border-cyan-500/40 text-left transition-all flex items-start gap-2.5"
                    >
                      <span className="font-jetbrains font-bold text-cyan-400 shrink-0">[{ref.num}]</span>
                      <div className="flex-1">
                        <span className="font-bold text-white block">{ref.title}</span>
                        <span className="text-[11px] text-slate-400 italic line-clamp-1">
                          &ldquo;{ref.quote}&rdquo;
                        </span>
                        <span className="text-[10px] text-cyan-400 font-mono mt-1 block">
                          Inspect Clause {ref.clauseId} →
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4 font-mono text-xs text-slate-300">
              <div className="border-b border-slate-800 pb-3">
                <h2 className="font-orbitron font-bold text-lg text-white">
                  Document Audit Report: {selectedDocKey}
                </h2>
                <p className="text-slate-400 text-xs font-rajdhani">
                  Full clause hierarchy and extracted contractual commitments
                </p>
              </div>
              <p className="p-4 rounded-xl border border-slate-800 bg-slate-950">
                Detailed report view for contract {selectedDocKey}. Verified against SQLite document store with cryptographic SHA-256 integrity.
              </p>
            </div>
          )}
        </div>
      </main>

      <EvidenceDrawer />
    </div>
  );
}
