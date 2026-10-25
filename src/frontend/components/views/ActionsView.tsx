"use client";

import React, { useState } from "react";
import {
  FileCheck,
  CheckCircle,
  XCircle,
  Clock,
  UserCheck,
  MapPin,
  Download,
  AlertTriangle,
  Send,
  Eye,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function ActionsView() {
  const { actions, approveAction, rejectAction, openEvidence } = useOdinStore();
  const [selectedActionId, setSelectedActionId] = useState(actions[0]?.id || "ACT-01");
  const [hoveredFootnote, setHoveredFootnote] = useState<number | null>(null);

  const activeAction = actions.find((a) => a.id === selectedActionId) || actions[0];

  const handleApprove = (id: string) => {
    approveAction(id);
    toast.success("Action Approved for Dispatch", {
      description: `${activeAction.title} authorized by General Counsel signatory check.`,
    });
  };

  const handleReject = (id: string) => {
    rejectAction(id, "Requires additional clause verification");
    toast.error("Action Notice Rejected", {
      description: "Returned to Tyr and Loki for clause re-drafting.",
    });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left List of Drafted Notices */}
      <div className="lg:col-span-4 space-y-3">
        <div className="p-3.5 rounded-xl border border-cyan-500/20 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-cyan-400" />
            <span className="font-rajdhani font-bold text-xs uppercase tracking-wider text-slate-200">
              DRAFTED ACTIONS ({actions.length})
            </span>
          </div>
          <span className="text-[10px] font-mono text-cyan-400">TYR DISPATCH</span>
        </div>

        <div className="space-y-2.5">
          {actions.map((act) => (
            <button
              key={act.id}
              onClick={() => setSelectedActionId(act.id)}
              className={`w-full p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                selectedActionId === act.id
                  ? "border-cyan-400 bg-cyan-950/40 shadow-lg shadow-cyan-500/10"
                  : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <Badge
                  variant="outline"
                  className={`text-[10px] font-mono ${
                    act.status === "APPROVED"
                      ? "border-emerald-500 text-emerald-400 bg-emerald-950"
                      : act.status === "REJECTED"
                      ? "border-rose-500 text-rose-400 bg-rose-950"
                      : "border-amber-500 text-amber-400 bg-amber-950"
                  }`}
                >
                  {act.status}
                </Badge>
                <span className="text-[11px] font-mono text-slate-400">
                  Target: {act.targetContract}
                </span>
              </div>

              <h4 className="font-rajdhani font-bold text-sm text-white leading-snug mb-1">
                {act.title}
              </h4>
              <p className="text-[11px] text-slate-400 truncate mb-2">
                To: {act.recipientName}
              </p>

              <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 border-t border-slate-800 pt-2">
                <span>Deadline: {act.sendByDeadline}</span>
                <span className="text-cyan-300 font-bold">{act.confidenceScore}% Score</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Center: Formal Letter Preview with Footnotes */}
      <div className="lg:col-span-5 hud-panel p-6 rounded-2xl flex flex-col justify-between">
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest block">
                FORMAL NOTICE DISPATCH PREVIEW
              </span>
              <h3 className="font-orbitron font-bold text-base text-white">
                {activeAction.title}
              </h3>
            </div>
            <Badge variant="outline" className="border-slate-700 text-slate-400 font-mono text-xs">
              TYPE: {activeAction.type.toUpperCase()}
            </Badge>
          </div>

          {/* Letter recipient block */}
          <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-950/80 font-mono text-xs text-slate-300 space-y-1">
            <p className="font-bold text-white">RECIPIENT: {activeAction.recipientName}</p>
            <p className="text-slate-400 text-[11px]">{activeAction.recipientEmail}</p>
            <p className="text-slate-400 text-[11px]">{activeAction.recipientAddress}</p>
          </div>

          {/* Verbatim Letter Body */}
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-950 font-mono text-xs text-slate-200 leading-relaxed whitespace-pre-wrap selection:bg-cyan-500/30 min-h-[220px]">
            {activeAction.letterBody}
          </div>

          {/* Footnotes Panel */}
          {activeAction.footnotes.length > 0 && (
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2">
              <span className="text-[10px] font-rajdhani font-bold uppercase tracking-wider text-slate-400 block">
                INLINE FOOTNOTE CITATIONS (HOVER / CLICK TO INSPECT)
              </span>
              <div className="space-y-1.5">
                {activeAction.footnotes.map((fn) => (
                  <div
                    key={fn.id}
                    onMouseEnter={() => setHoveredFootnote(fn.id)}
                    onMouseLeave={() => setHoveredFootnote(null)}
                    onClick={() => openEvidence(fn.clauseId)}
                    className="p-2 rounded border border-slate-800 hover:border-cyan-500/40 bg-slate-950 cursor-pointer text-xs font-mono transition-all flex items-start gap-2"
                  >
                    <span className="text-cyan-400 font-bold">[{fn.id}]</span>
                    <div className="flex-1">
                      <span className="text-slate-300 font-bold">{fn.clauseId}</span>:{" "}
                      <span className="text-slate-400">{fn.text}</span>
                      <p className="text-[10px] text-amber-300/80 italic mt-0.5">&ldquo;{fn.quote}&rdquo;</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Action Controls Bar */}
        <div className="pt-4 border-t border-slate-800 flex items-center justify-between gap-3">
          <Button
            size="sm"
            variant="outline"
            onClick={() => alert(`Exporting signed letter copy for ${activeAction.title}...`)}
            className="border-slate-700 text-xs font-rajdhani"
          >
            <Download className="w-3.5 h-3.5 mr-1 text-cyan-400" /> Export PDF
          </Button>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={activeAction.status === "REJECTED"}
              onClick={() => handleReject(activeAction.id)}
              className="border-rose-800 text-rose-400 hover:bg-rose-950/60 text-xs font-rajdhani"
            >
              <XCircle className="w-3.5 h-3.5 mr-1" /> Reject Notice
            </Button>
            <Button
              size="sm"
              disabled={activeAction.status === "APPROVED"}
              onClick={() => handleApprove(activeAction.id)}
              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs font-rajdhani"
            >
              <CheckCircle className="w-3.5 h-3.5 mr-1" /> Approve & Sign
            </Button>
          </div>
        </div>
      </div>

      {/* Right: Validation & Verification Checks Rail */}
      <div className="lg:col-span-3 space-y-4">
        {/* Compliance Checks Card */}
        <div className="hud-panel p-5 rounded-2xl space-y-4">
          <span className="font-rajdhani text-xs font-bold uppercase tracking-wider text-cyan-300 block border-b border-slate-800 pb-2">
            LEGAL VALIDATION GATES
          </span>

          {/* Confidence Meter */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-jetbrains">
              <span className="text-slate-400">Tyr Formulation Confidence</span>
              <span className="text-emerald-400 font-bold">{activeAction.confidenceScore}%</span>
            </div>
            <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden">
              <div
                style={{ width: `${activeAction.confidenceScore}%` }}
                className="h-full bg-cyan-400 rounded-full shadow-sm shadow-cyan-400"
              />
            </div>
          </div>

          {/* Signatory Check */}
          <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-1 text-xs font-mono">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-cyan-400" /> Authorized Signatory
              </span>
              {activeAction.signatoryValid ? (
                <Badge className="bg-emerald-950 text-emerald-400 border-emerald-600 text-[10px]">
                  VERIFIED
                </Badge>
              ) : (
                <Badge className="bg-rose-950 text-rose-400 border-rose-600 text-[10px]">
                  INVALID
                </Badge>
              )}
            </div>
            <p className="text-slate-300 font-bold text-[11px] pt-1">{activeAction.signatoryName}</p>
            <p className="text-[10px] text-slate-500">Cross-referenced with Quillhub Delaware charter</p>
          </div>

          {/* Notice Address Check */}
          <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-1 text-xs font-mono">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-cyan-400" /> Formal Notice Address
              </span>
              {activeAction.noticeAddressValid ? (
                <Badge className="bg-emerald-950 text-emerald-400 border-emerald-600 text-[10px]">
                  MATCHED
                </Badge>
              ) : (
                <Badge className="bg-amber-950 text-amber-400 border-amber-600 text-[10px]">
                  UNVERIFIED
                </Badge>
              )}
            </div>
            <p className="text-slate-300 text-[11px] pt-1">{activeAction.recipientAddress}</p>
            <p className="text-[10px] text-slate-500">Matches Section 12 notice requirements of {activeAction.targetContract}</p>
          </div>

          {/* Human Approval Required Badge */}
          {activeAction.needsApproval && (
            <div className="p-3 rounded-lg border border-amber-500/40 bg-amber-950/20 text-amber-300 text-xs font-mono flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>Requires human approval before transmission</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
