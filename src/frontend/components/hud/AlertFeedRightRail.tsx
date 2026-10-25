"use client";

import React, { useState } from "react";
import {
  Bell,
  CheckCircle,
  Clock,
  Eye,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  VolumeX,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function AlertFeedRightRail() {
  const {
    alerts,
    acknowledgeAlert,
    snoozeAlert,
    openEvidence,
  } = useOdinStore();

  const [showSuppressed, setShowSuppressed] = useState(false);

  // Filter and sort active alerts
  const activeAlerts = alerts
    .filter((a) => !a.suppressed)
    .sort((a, b) => {
      const sevOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      if (sevOrder[a.severity] !== sevOrder[b.severity]) {
        return sevOrder[a.severity] - sevOrder[b.severity];
      }
      return a.countdownDays - b.countdownDays;
    });

  const suppressedAlerts = alerts.filter((a) => a.suppressed);

  const getSeverityStripe = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return "border-l-4 border-l-rose-500 bg-rose-950/20";
      case "HIGH":
        return "border-l-4 border-l-amber-500 bg-amber-950/20";
      case "MEDIUM":
        return "border-l-4 border-l-yellow-400 bg-yellow-950/20";
      default:
        return "border-l-4 border-l-blue-400 bg-blue-950/20";
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return "bg-rose-950 text-rose-400 border-rose-800";
      case "HIGH":
        return "bg-amber-950 text-amber-400 border-amber-800";
      case "MEDIUM":
        return "bg-yellow-950 text-yellow-400 border-yellow-800";
      default:
        return "bg-blue-950 text-blue-400 border-blue-800";
    }
  };

  return (
    <aside className="w-80 shrink-0 flex flex-col h-[calc(100vh-140px)] border-l border-cyan-500/20 bg-slate-950/80 backdrop-blur-md">
      {/* Header */}
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-cyan-400" />
          <span className="font-rajdhani font-bold text-xs uppercase tracking-wider text-slate-200">
            TACTICAL ALERTS ({activeAlerts.length})
          </span>
        </div>
        <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-1.5 py-0.5 rounded border border-cyan-500/30">
          HEIMDALL FEED
        </span>
      </div>

      {/* Alert Cards Scroll Container */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {activeAlerts.map((alert) => (
          <div
            key={alert.id}
            className={`p-3 rounded-lg border border-slate-800 transition-all ${getSeverityStripe(
              alert.severity
            )} ${alert.acknowledged ? "opacity-60" : "hover:border-slate-700"}`}
          >
            {/* Top row: badge + countdown */}
            <div className="flex items-center justify-between gap-1 mb-1.5">
              <div className="flex items-center gap-1.5">
                <Badge variant="outline" className={`text-[10px] font-mono px-1.5 py-0 ${getSeverityBadge(alert.severity)}`}>
                  {alert.severity}
                </Badge>
                <span className="text-[11px] font-mono font-bold text-cyan-300">
                  {alert.contractId}
                </span>
              </div>
              <span className={`text-[11px] font-jetbrains font-bold ${
                alert.countdownDays <= 3 ? "text-rose-400 animate-pulse" : "text-slate-400"
              }`}>
                {alert.countdownDays < 0
                  ? `ELAPSED (${Math.abs(alert.countdownDays)}d)`
                  : `T-${alert.countdownDays}d`}
              </span>
            </div>

            {/* Title */}
            <h4 className="font-rajdhani font-bold text-xs text-white leading-tight mb-1">
              {alert.title}
            </h4>

            {/* Snippet */}
            <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed mb-2.5">
              {alert.description}
            </p>

            {/* Action Bar */}
            <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[10px]">
              <span className="text-slate-500 font-mono">Src: {alert.source}</span>
              <div className="flex items-center gap-1">
                {alert.clauseId && (
                  <button
                    onClick={() => openEvidence(alert.clauseId!)}
                    title="Inspect Source Clause Evidence"
                    className="px-1.5 py-0.5 rounded text-cyan-400 hover:text-white hover:bg-slate-800 transition-all flex items-center gap-0.5"
                  >
                    <Eye className="w-3 h-3" />
                    <span>Evidence</span>
                  </button>
                )}
                {!alert.acknowledged && (
                  <button
                    onClick={() => acknowledgeAlert(alert.id)}
                    title="Acknowledge Alert"
                    className="px-1.5 py-0.5 rounded text-slate-400 hover:text-emerald-400 hover:bg-slate-800 transition-all flex items-center gap-0.5"
                  >
                    <CheckCircle className="w-3 h-3" />
                    <span>Ack</span>
                  </button>
                )}
                <button
                  onClick={() => snoozeAlert(alert.id)}
                  title="Snooze for 7 days"
                  className="px-1.5 py-0.5 rounded text-slate-400 hover:text-amber-400 hover:bg-slate-800 transition-all"
                >
                  Snooze
                </button>
              </div>
            </div>
          </div>
        ))}

        {/* Collapsed Suppressed Noise Section */}
        <div className="pt-2 border-t border-slate-800/80">
          <button
            onClick={() => setShowSuppressed(!showSuppressed)}
            className="w-full flex items-center justify-between p-2 rounded-lg bg-slate-900/50 hover:bg-slate-900 border border-slate-800 text-xs text-slate-400 font-rajdhani uppercase tracking-wider"
          >
            <div className="flex items-center gap-1.5">
              <VolumeX className="w-3.5 h-3.5 text-slate-500" />
              <span>Suppressed Noise ({suppressedAlerts.length})</span>
            </div>
            {showSuppressed ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>

          {showSuppressed && (
            <div className="mt-2 space-y-2">
              {suppressedAlerts.map((item) => (
                <div
                  key={item.id}
                  className="p-2.5 rounded-lg border border-slate-900 bg-slate-950 text-[11px] text-slate-400 opacity-70"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-300 truncate">{item.title}</span>
                    <Badge variant="outline" className="text-[9px] py-0 border-slate-800 text-slate-500">
                      FILTERED
                    </Badge>
                  </div>
                  <p className="text-[10px] text-slate-500 leading-tight">
                    Reason: {item.suppressionReason}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
