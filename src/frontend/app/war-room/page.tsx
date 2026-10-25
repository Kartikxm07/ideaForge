"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { HudHeader } from "@/components/hud/HudHeader";
import { KpiStrip } from "@/components/hud/KpiStrip";
import { TimeSlider } from "@/components/hud/TimeSlider";
import { AlertFeedRightRail } from "@/components/hud/AlertFeedRightRail";
import { EvidenceDrawer } from "@/components/hud/EvidenceDrawer";
import { ClauseDiffModal } from "@/components/hud/ClauseDiffModal";
import { AddEventModal } from "@/components/hud/AddEventModal";
import { AddContractModal } from "@/components/hud/AddContractModal";
import { ContractGraphView } from "@/components/views/ContractGraphView";
import { ExposureView } from "@/components/views/ExposureView";
import { TimelineView } from "@/components/views/TimelineView";
import { DebateView } from "@/components/views/DebateView";
import { ActionsView } from "@/components/views/ActionsView";
import { TraceView } from "@/components/views/TraceView";
import { PlanView } from "@/components/views/PlanView";
import { useOdinStore, WarRoomTab } from "@/store/useOdinStore";
import {
  Layers,
  DollarSign,
  Clock,
  Scale,
  FileCheck,
  Terminal,
  Cpu,
  FilePlus,
} from "lucide-react";

export default function WarRoomPage() {
  const { activeTab, setActiveTab } = useOdinStore();
  const [contractModalOpen, setContractModalOpen] = useState(false);

  const navItems: { id: WarRoomTab; label: string; icon: any }[] = [
    { id: "graph",    label: "Contract Graph",   icon: Layers },
    { id: "exposure", label: "Risk Exposure",    icon: DollarSign },
    { id: "timeline", label: "Timeline",         icon: Clock },
    { id: "debate",   label: "Debate Council",   icon: Scale },
    { id: "actions",  label: "Drafted Actions",  icon: FileCheck },
    { id: "plan",     label: "Work Plan",        icon: Cpu },
    { id: "trace",    label: "Telemetry",        icon: Terminal },
  ];

  const renderActiveView = () => {
    switch (activeTab) {
      case "graph":    return <ContractGraphView />;
      case "exposure": return <ExposureView />;
      case "timeline": return <TimelineView />;
      case "debate":   return <DebateView />;
      case "actions":  return <ActionsView />;
      case "plan":     return <PlanView />;
      case "trace":    return <TraceView />;
      default:         return <ContractGraphView />;
    }
  };

  return (
    <div className="flex flex-col min-h-dvh bg-page text-[#1A1208]">
      <HudHeader />

      <main className="flex-1 max-w-[1600px] w-full mx-auto px-5 pt-5 pb-28 space-y-5">

        {/* Page title row */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="heading-xl">Financial & Contract Intelligence</h1>
            <p className="text-sm text-[#8A7355] mt-0.5">
              Institutional exposure analytics and legal compliance solutions · Quillhub Inc.
            </p>
          </div>

          {/* Add Contract CTA */}
          <button
            onClick={() => setContractModalOpen(true)}
            className="btn-primary flex items-center gap-2 shadow-lg shadow-amber-500/20"
          >
            <FilePlus className="w-4 h-4" />
            Add Contract
          </button>
        </div>

        {/* Separator */}
        <div className="sep-gold" />

        {/* KPI Strip */}
        <KpiStrip />

        {/* Main layout */}
        <div className="flex gap-5 items-start">

          {/* Left Sidebar Nav */}
          <nav className="w-48 shrink-0 card rounded-xl p-2 space-y-0.5">
            <p className="label-caps px-3 pt-2 pb-1.5 border-b border-[rgba(212,160,23,0.14)] mb-1">
              Views
            </p>
            {navItems.map((item) => {
              const active = activeTab === item.id;
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`sidebar-item ${active ? "active" : ""}`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${active ? "text-amber-600" : "text-[#8A7355]"}`} />
                  <span className="text-sm">{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Center View */}
          <div className="flex-1 min-w-0">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                {renderActiveView()}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Right Rail */}
          <AlertFeedRightRail />
        </div>
      </main>

      {/* Modals & Drawers */}
      <EvidenceDrawer />
      <ClauseDiffModal />
      <AddEventModal />
      <AddContractModal
        open={contractModalOpen}
        onClose={() => setContractModalOpen(false)}
        onAdd={(c) => {
          console.log("Contract added:", c);
        }}
      />

      {/* Bottom Timeline */}
      <TimeSlider />
    </div>
  );
}
