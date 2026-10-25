"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { HudHeader } from "@/components/hud/HudHeader";
import {
  Shield,
  Building,
  UploadCloud,
  FileSpreadsheet,
  Clock,
  Play,
  CheckCircle2,
  AlertTriangle,
  FileText,
  UserCheck,
  ArrowRight,
  ArrowLeft,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function NewCasePage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);

  // Form State
  const [company, setCompany] = useState({
    legalName: "Quillhub Inc.",
    jurisdiction: "Delaware, USA",
    address: "450 Mission Street, Suite 1200, San Francisco, CA 94105",
    signatories: "Elena Rostova (CEO), Marcus Thorne (CLO & General Counsel), Siddharth Nair (VP Eng)",
    noticeEmails: "legal-notices@quillhub.com, compliance@quillhub.com",
    insurer: "Chubb Cyber Shield",
    policyNo: "CH-CYB-2026-99",
    coverage: "$500,000",
    expiry: "2026-12-31",
  });

  const steps = [
    { num: 1, title: "Company Profile" },
    { num: 2, title: "Upload Contracts" },
    { num: 3, title: "Ledger & Holidays" },
    { num: 4, title: "Set Clock" },
    { num: 5, title: "Validation & Launch" },
  ];

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 bg-hex-grid flex flex-col">
      <HudHeader />

      <main className="flex-1 max-w-5xl w-full mx-auto p-6 space-y-8">
        {/* Title */}
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-4">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-400 block">
              INGESTION PIPELINE • STEPPER WIZARD
            </span>
            <h1 className="font-orbitron font-bold text-2xl text-white">
              NEW CASE DOSSIER ONBOARDING
            </h1>
          </div>
          <Badge className="bg-cyan-950 text-cyan-300 border-cyan-600 font-mono text-xs">
            STEP {currentStep} OF 5
          </Badge>
        </div>

        {/* Stepper Progress Bar */}
        <div className="grid grid-cols-5 gap-2">
          {steps.map((st) => (
            <div
              key={st.num}
              onClick={() => setCurrentStep(st.num)}
              className={`p-3 rounded-lg border text-xs font-rajdhani uppercase font-bold tracking-wider cursor-pointer transition-all ${
                currentStep === st.num
                  ? "border-cyan-400 bg-cyan-950/80 text-cyan-200 shadow-md shadow-cyan-500/20"
                  : currentStep > st.num
                  ? "border-emerald-500/50 bg-emerald-950/30 text-emerald-300"
                  : "border-slate-800 bg-slate-900/40 text-slate-500"
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                {currentStep > st.num ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <span className="font-mono text-[11px]">0{st.num}</span>
                )}
              </div>
              <span className="truncate block">{st.title}</span>
            </div>
          ))}
        </div>

        {/* Step 1: Company Profile Form */}
        {currentStep === 1 && (
          <div className="hud-panel p-6 rounded-2xl space-y-5">
            <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
              <Building className="w-5 h-5 text-cyan-400" />
              Company Legal Entity & Signatories
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-rajdhani">
              <div>
                <label className="block text-slate-400 font-bold uppercase mb-1">Legal Name</label>
                <Input
                  value={company.legalName}
                  onChange={(e) => setCompany({ ...company, legalName: e.target.value })}
                  className="bg-slate-950 border-slate-800 text-xs font-jetbrains"
                />
              </div>
              <div>
                <label className="block text-slate-400 font-bold uppercase mb-1">Jurisdiction</label>
                <Input
                  value={company.jurisdiction}
                  onChange={(e) => setCompany({ ...company, jurisdiction: e.target.value })}
                  className="bg-slate-950 border-slate-800 text-xs font-jetbrains"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-slate-400 font-bold uppercase mb-1">Corporate Headquarters Address</label>
                <Input
                  value={company.address}
                  onChange={(e) => setCompany({ ...company, address: e.target.value })}
                  className="bg-slate-950 border-slate-800 text-xs font-jetbrains"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-slate-400 font-bold uppercase mb-1">Authorized Legal Signatories</label>
                <Input
                  value={company.signatories}
                  onChange={(e) => setCompany({ ...company, signatories: e.target.value })}
                  className="bg-slate-950 border-slate-800 text-xs font-jetbrains"
                />
              </div>
              <div>
                <label className="block text-slate-400 font-bold uppercase mb-1">Official Notice Emails</label>
                <Input
                  value={company.noticeEmails}
                  onChange={(e) => setCompany({ ...company, noticeEmails: e.target.value })}
                  className="bg-slate-950 border-slate-800 text-xs font-jetbrains"
                />
              </div>
              <div>
                <label className="block text-slate-400 font-bold uppercase mb-1">Primary Cyber Risk Insurer</label>
                <Input
                  value={company.insurer}
                  onChange={(e) => setCompany({ ...company, insurer: e.target.value })}
                  className="bg-slate-950 border-slate-800 text-xs font-jetbrains"
                />
              </div>
              <div>
                <label className="block text-slate-400 font-bold uppercase mb-1">Policy Coverage Limit</label>
                <Input
                  value={company.coverage}
                  onChange={(e) => setCompany({ ...company, coverage: e.target.value })}
                  className="bg-slate-950 border-slate-800 text-xs font-jetbrains"
                />
              </div>
              <div>
                <label className="block text-slate-400 font-bold uppercase mb-1">Policy Expiration Date</label>
                <Input
                  value={company.expiry}
                  onChange={(e) => setCompany({ ...company, expiry: e.target.value })}
                  className="bg-slate-950 border-slate-800 text-xs font-jetbrains"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Upload Contracts */}
        {currentStep === 2 && (
          <div className="hud-panel p-6 rounded-2xl space-y-5">
            <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-cyan-400" />
              Upload Multi-Agreement Portfolio (8 Files Staged)
            </h3>

            <div className="p-8 border-2 border-dashed border-cyan-500/40 rounded-xl bg-cyan-950/10 text-center space-y-2">
              <FileText className="w-8 h-8 text-cyan-400 mx-auto" />
              <p className="text-sm font-bold text-white font-rajdhani uppercase">
                Drag and Drop Contract PDF & Text Bundles
              </p>
              <p className="text-xs text-slate-400 font-mono">
                Supports STD.txt, A1.txt (Hosting), A2.txt (SLA), A3.txt, B1.txt, B2.txt, C1.txt, D1.txt
              </p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { id: "STD", title: "Master Standard Terms", cat: "standard" },
                { id: "A1", title: "StratoNode Hosting", cat: "upstream" },
                { id: "A2", title: "StratoNode SLA", cat: "upstream" },
                { id: "A3", title: "SLA Amendment No. 1", cat: "upstream" },
                { id: "B1", title: "Harbor Retail Route", cat: "customer" },
                { id: "B2", title: "Harbor Security Addendum", cat: "customer" },
                { id: "C1", title: "FleetFlow Commercial", cat: "customer" },
                { id: "D1", title: "Apex Contractor Agreement", cat: "contractor" },
              ].map((doc) => (
                <div key={doc.id} className="p-3 rounded-lg border border-slate-800 bg-slate-950 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-cyan-300 font-jetbrains">{doc.id}</span>
                    <p className="text-[10px] text-slate-400 truncate">{doc.title}</p>
                  </div>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Ledger & Holidays */}
        {currentStep === 3 && (
          <div className="hud-panel p-6 rounded-2xl space-y-5">
            <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
              Financial Transaction Ledger & Business Holidays
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-950 space-y-2">
                <span className="font-bold text-xs text-white uppercase font-rajdhani block">
                  payments_ledger.csv (Staged)
                </span>
                <p className="text-xs text-slate-400 font-mono">
                  Contains 24 historical billing cycles across StratoNode, Harbor Retail, FleetFlow, and Apex Systems.
                </p>
                <div className="text-[11px] font-mono text-emerald-400">
                  Status: 100% Hash Matched • Zero Duplicate Invoices
                </div>
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-950 space-y-2">
                <span className="font-bold text-xs text-white uppercase font-rajdhani block">
                  holidays.csv (Staged)
                </span>
                <p className="text-xs text-slate-400 font-mono">
                  Observed US Federal & Delaware Court business holidays calibrated for notice window calculation.
                </p>
                <div className="text-[11px] font-mono text-emerald-400">
                  Status: 11 Observed Holidays Loaded
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Set Clock */}
        {currentStep === 4 && (
          <div className="hud-panel p-6 rounded-2xl space-y-5">
            <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-400" />
              Configure Simulated Clock Milestones
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { id: "CP1", date: "2026-10-01", label: "Checkpoint 1: Baseline Portfolio", desc: "Contract execution & initial hosting setup." },
                { id: "CP2", date: "2026-11-15", label: "Checkpoint 2: Drop 1 Outage", desc: "US-East outage occurs; Harbor issues breach notice." },
                { id: "CP3", date: "2027-01-10", label: "Checkpoint 3: Drop 2 Rulings", desc: "Tyr rulings enforced & cure actions verified." },
              ].map((cp) => (
                <div key={cp.id} className="p-4 rounded-xl border border-slate-800 bg-slate-950 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-jetbrains font-bold text-xs text-amber-400">{cp.id}</span>
                    <span className="text-xs font-mono text-slate-400">{cp.date}</span>
                  </div>
                  <h4 className="font-bold text-sm text-white font-rajdhani">{cp.label}</h4>
                  <p className="text-xs text-slate-400">{cp.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 5: Validation Screen & Launch */}
        {currentStep === 5 && (
          <div className="hud-panel p-6 rounded-2xl space-y-5 border-emerald-500/30">
            <h3 className="font-orbitron font-bold text-base text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              Pre-Analysis Validation Screen
            </h3>

            <div className="space-y-3 font-jetbrains text-xs">
              <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/40 text-emerald-300 flex items-center justify-between">
                <span>Malformed File Check:</span>
                <span className="font-bold">0 Errors (All 8 contracts structurally valid)</span>
              </div>
              <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/40 text-emerald-300 flex items-center justify-between">
                <span>Duplicate Ledger Rows:</span>
                <span className="font-bold">0 Duplicates (Full transaction integrity)</span>
              </div>
              <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-500/40 text-amber-300 flex items-center justify-between">
                <span>Quarantined Noise Events:</span>
                <span className="font-bold">4 Marketing / Webhook payloads isolated</span>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800 flex justify-end">
              <Button
                onClick={() => router.push("/analysis")}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-orbitron font-bold text-xs uppercase tracking-wider px-6 h-10 shadow-lg shadow-cyan-500/30"
              >
                <Play className="w-4 h-4 mr-2 fill-current" />
                Launch Autonomous Analysis
              </Button>
            </div>
          </div>
        )}

        {/* Step Navigation Bar */}
        <div className="flex items-center justify-between pt-4">
          <Button
            variant="outline"
            disabled={currentStep === 1}
            onClick={() => setCurrentStep(currentStep - 1)}
            className="border-slate-800 text-slate-400 text-xs font-rajdhani font-bold"
          >
            <ArrowLeft className="w-4 h-4 mr-1.5" /> Previous Step
          </Button>

          {currentStep < 5 && (
            <Button
              onClick={() => setCurrentStep(currentStep + 1)}
              className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-rajdhani font-bold"
            >
              Next Step <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          )}
        </div>
      </main>
    </div>
  );
}
