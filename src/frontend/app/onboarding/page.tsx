"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Building2,
  FileText,
  Upload,
  CheckCircle2,
  X,
  Plus,
  ArrowRight,
  Scale,
  ShieldCheck,
  ChevronRight,
  Lock,
} from "lucide-react";

interface Signatory {
  name: string;
  role: string;
}

interface ContractItem {
  name: string;
  content: string;
  size: number;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);

  // Form states
  const [legalName, setLegalName] = useState("");
  const [industry, setIndustry] = useState("Finance & Fintech");
  const [jurisdiction, setJurisdiction] = useState("Delaware, USA");
  const [email, setEmail] = useState("");
  const [signatories, setSignatories] = useState<Signatory[]>([
    { name: "", role: "Managing Director" },
  ]);

  // Contracts
  const [contracts, setContracts] = useState<ContractItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addSignatory = () => {
    setSignatories((prev) => [...prev, { name: "", role: "General Counsel" }]);
  };

  const updateSignatory = (idx: number, field: "name" | "role", val: string) => {
    setSignatories((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, [field]: val } : s))
    );
  };

  const removeSignatory = (idx: number) => {
    setSignatories((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleFileUpload = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setContracts((prev) => [
          ...prev,
          {
            name: file.name,
            content: (e.target?.result as string) || "",
            size: file.size,
          },
        ]);
      };
      reader.readAsText(file);
    });
  };

  const canProceedStep1 = legalName.trim().length > 0;

  return (
    <div className="min-h-screen bg-[#FDFBF7] text-[#18181B] flex flex-col justify-between">
      {/* Top minimal header */}
      <header className="border-b border-black/[0.06] bg-white/70 backdrop-blur-md px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#D4A017] flex items-center justify-center text-white font-semibold">
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">ODIN</h1>
            <p className="text-[11px] text-zinc-500 font-medium">Financial Solutions</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className={`px-2.5 py-1 rounded-md font-medium ${step === 1 ? "bg-amber-100 text-amber-900 font-semibold" : "text-zinc-600"}`}>
            1. Organization
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-zinc-400" />
          <span className={`px-2.5 py-1 rounded-md font-medium ${step === 2 ? "bg-amber-100 text-amber-900 font-semibold" : "text-zinc-600"}`}>
            2. Contracts
          </span>
        </div>
      </header>

      {/* Main card */}
      <main className="flex-1 max-w-2xl w-full mx-auto px-6 py-10 flex flex-col justify-center">
        {step === 1 ? (
          <div className="bg-white border border-black/[0.08] rounded-2xl p-8 shadow-sm">
            <div className="mb-6">
              <span className="text-xs font-semibold tracking-wider uppercase text-amber-800">
                Setup Organization
              </span>
              <h2 className="text-xl font-bold text-zinc-900 mt-1">
                Enter Entity & Signatory Information
              </h2>
              <p className="text-xs text-zinc-500 mt-1">
                Provide legal structure data to anchor compliance scanning.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1.5">
                  Legal Entity Name
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={legalName}
                    onChange={(e) => setLegalName(e.target.value)}
                    placeholder="e.g. Asgard Strategic Holdings LLC"
                    className="w-full pl-9 pr-3.5 py-2.5 rounded-lg border border-zinc-200 text-sm focus:outline-none focus:border-amber-600 focus:ring-1 focus:ring-amber-600"
                  />
                  <Building2 className="w-4 h-4 text-zinc-400 absolute left-3 top-3" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1.5">
                    Industry / Sector
                  </label>
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 text-sm focus:outline-none focus:border-amber-600"
                  >
                    <option>Finance & Fintech</option>
                    <option>Asset Management</option>
                    <option>Corporate Law</option>
                    <option>Commercial Real Estate</option>
                    <option>Logistics & Supply</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1.5">
                    Jurisdiction
                  </label>
                  <input
                    type="text"
                    value={jurisdiction}
                    onChange={(e) => setJurisdiction(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 text-sm focus:outline-none focus:border-amber-600"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-semibold text-zinc-700">
                    Authorized Signatories
                  </label>
                  <button
                    type="button"
                    onClick={addSignatory}
                    className="text-xs font-semibold text-amber-700 hover:text-amber-800 flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add
                  </button>
                </div>

                <div className="space-y-2">
                  {signatories.map((sig, idx) => (
                    <div key={idx} className="flex gap-2 items-center">
                      <input
                        type="text"
                        placeholder="Signatory Full Name"
                        value={sig.name}
                        onChange={(e) => updateSignatory(idx, "name", e.target.value)}
                        className="flex-1 px-3 py-2 rounded-lg border border-zinc-200 text-xs focus:outline-none focus:border-amber-600"
                      />
                      <input
                        type="text"
                        placeholder="Designation"
                        value={sig.role}
                        onChange={(e) => updateSignatory(idx, "role", e.target.value)}
                        className="w-1/3 px-3 py-2 rounded-lg border border-zinc-200 text-xs focus:outline-none focus:border-amber-600"
                      />
                      {signatories.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeSignatory(idx)}
                          className="p-1.5 text-zinc-400 hover:text-red-500 rounded"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-8 flex justify-end">
              <button
                type="button"
                disabled={!canProceedStep1}
                onClick={() => setStep(2)}
                className="inline-flex items-center gap-2 bg-[#D4A017] hover:bg-[#B8880E] disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm px-6 py-2.5 rounded-lg shadow-sm transition-all"
              >
                <span>Continue to Contracts</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white border border-black/[0.08] rounded-2xl p-8 shadow-sm">
            <div className="mb-6">
              <span className="text-xs font-semibold tracking-wider uppercase text-amber-800">
                Contract Ingestion
              </span>
              <h2 className="text-xl font-bold text-zinc-900 mt-1">
                Upload Master Agreements & Terms
              </h2>
              <p className="text-xs text-zinc-500 mt-1">
                Drag and drop your agreements (.txt / documents) to scan for obligations.
              </p>
            </div>

            {/* Dropzone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                handleFileUpload(e.dataTransfer.files);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                isDragging
                  ? "border-amber-600 bg-amber-50/50"
                  : "border-zinc-300 hover:border-zinc-400 bg-zinc-50/50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".txt,.doc,.docx,.pdf"
                className="hidden"
                onChange={(e) => handleFileUpload(e.target.files)}
              />
              <Upload className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
              <p className="text-sm font-semibold text-zinc-700">
                Click to browse or drop agreements here
              </p>
              <p className="text-xs text-zinc-400 mt-1">
                Accepts text files and contracts
              </p>
            </div>

            {/* Ingested List */}
            {contracts.length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-xs font-semibold text-zinc-600">Loaded Documents ({contracts.length})</p>
                {contracts.map((c, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 rounded-lg border border-zinc-200 bg-zinc-50/70 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-amber-700" />
                      <span className="font-medium text-zinc-800">{c.name}</span>
                      <span className="text-zinc-400 text-[10px]">({Math.round(c.size / 1024)} KB)</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setContracts((prev) => prev.filter((_, idx) => idx !== i))}
                      className="text-zinc-400 hover:text-red-500"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-8 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs font-semibold text-zinc-500 hover:text-zinc-800"
              >
                Back
              </button>

              <button
                type="button"
                onClick={() => router.push("/war-room")}
                className="inline-flex items-center gap-2 bg-[#D4A017] hover:bg-[#B8880E] text-white font-semibold text-sm px-6 py-2.5 rounded-lg shadow-sm transition-all"
              >
                <span>Launch Analytics</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </main>

      <footer className="text-center py-4 text-xs text-zinc-400">
        ODIN Platform · Institutional Financial Solutions
      </footer>
    </div>
  );
}
