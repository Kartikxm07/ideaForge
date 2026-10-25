"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Building2, User, MapPin, Mail, Phone, Shield,
  FileText, Upload, CheckCircle2, X, Plus, Trash2,
  ChevronRight, ArrowRight, Loader2, Zap, Scale,
  AlertCircle, RefreshCw, Activity, BarChart3, FilePlus,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────
interface Signatory { name: string; role: string; }
interface ContractFile { name: string; label: string; content: string; size: number; }

interface CompanyForm {
  legalName: string;
  industry: string;
  jurisdiction: string;
  address: string;
  email: string;
  phone: string;
  signatories: Signatory[];
  insurerName: string;
  policyNumber: string;
  coverage: string;
}

// ─── Agent definitions ───────────────────────────────────
const AGENTS = [
  {
    id: "odin",
    name: "Odin",
    role: "Orchestrator",
    color: "#D4A017",
    bgLight: "#FFFBEF",
    icon: Scale,
    tasks: [
      "Initialising case context…",
      "Building execution plan…",
      "Routing to sub-agents…",
      "Monitoring convergence…",
      "Finalising synthesis…",
    ],
  },
  {
    id: "thor",
    name: "Thor",
    role: "Clause Extractor",
    color: "#1D72AA",
    bgLight: "#EFF6FF",
    icon: FileText,
    tasks: [
      "Parsing contract structure…",
      "Identifying key clauses…",
      "Tagging SLA obligations…",
      "Scoring clause confidence…",
      "Indexing fact database…",
    ],
  },
  {
    id: "norns",
    name: "Norns",
    role: "Timeline Keeper",
    color: "#065F46",
    bgLight: "#ECFDF5",
    icon: Activity,
    tasks: [
      "Loading calendar data…",
      "Mapping notice windows…",
      "Calibrating deadlines…",
      "Computing business days…",
      "Locking timeline…",
    ],
  },
  {
    id: "loki",
    name: "Loki",
    role: "Conflict Finder",
    color: "#6D28D9",
    bgLight: "#F5F3FF",
    icon: AlertCircle,
    tasks: [
      "Scanning cross-contract…",
      "Identifying asymmetries…",
      "Testing clause conflicts…",
      "Generating challenges…",
      "Finalising risk report…",
    ],
  },
  {
    id: "heimdall",
    name: "Heimdall",
    role: "Event Watcher",
    color: "#0E7490",
    bgLight: "#ECFEFF",
    icon: RefreshCw,
    tasks: [
      "Loading event feed…",
      "Filtering noise events…",
      "Validating breach claims…",
      "Mapping to obligations…",
      "Promoting findings…",
    ],
  },
  {
    id: "tyr",
    name: "Tyr",
    role: "Arbiter",
    color: "#C0162C",
    bgLight: "#FFF5F5",
    icon: BarChart3,
    tasks: [
      "Reviewing disputes…",
      "Applying legal rules…",
      "Drafting notices…",
      "Computing exposure…",
      "Publishing rulings…",
    ],
  },
];

const INDUSTRIES = [
  "Technology / SaaS", "Financial Services", "Healthcare", "Legal Services",
  "Retail / E-commerce", "Manufacturing", "Real Estate", "Consulting",
  "Media & Entertainment", "Other",
];

// ─── Step indicator ───────────────────────────────────────
function StepBar({ step }: { step: number }) {
  const steps = ["Company Details", "Upload Contracts", "Analysis"];
  return (
    <div className="flex items-center gap-0 mb-10">
      {steps.map((label, i) => {
        const idx = i + 1;
        const done = idx < step;
        const active = idx === step;
        return (
          <React.Fragment key={idx}>
            <div className="flex items-center gap-2.5">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300 ${
                done   ? "bg-emerald-500 text-white shadow-md shadow-emerald-200" :
                active ? "bg-gradient-to-br from-amber-400 to-amber-600 text-white shadow-md shadow-amber-200" :
                         "bg-[#F2EDE1] text-[#8A7355]"
              }`}>
                {done ? <CheckCircle2 className="w-4 h-4" /> : idx}
              </div>
              <span className={`text-sm font-medium hidden sm:block ${active ? "text-[#1A1208]" : "text-[#8A7355]"}`}>
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`flex-1 h-px mx-4 transition-colors duration-500 ${done ? "bg-emerald-300" : "bg-[#E8E0CE]"}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Animated agent card ──────────────────────────────────
function AgentCard({ agent, progress, taskIndex, done }: {
  agent: typeof AGENTS[0]; progress: number; taskIndex: number; done: boolean;
}) {
  const Icon = agent.icon;
  const circumference = 2 * Math.PI * 28;
  const offset = circumference - (circumference * progress) / 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-5 flex flex-col items-center text-center gap-3"
      style={{ borderColor: done ? "#10B981" : `${agent.color}30` }}
    >
      {/* Progress ring */}
      <div className="relative w-18 h-18 flex items-center justify-center" style={{ width: 72, height: 72 }}>
        <svg width="72" height="72" className="-rotate-90">
          <circle cx="36" cy="36" r="28" stroke="#F2EDE1" strokeWidth="5" fill="none" />
          <motion.circle
            cx="36" cy="36" r="28"
            stroke={done ? "#10B981" : agent.color}
            strokeWidth="5" fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          {done
            ? <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            : <Icon className="w-5 h-5" style={{ color: agent.color }} />
          }
        </div>
      </div>

      <div>
        <p className="font-bold text-[#1A1208] text-sm">{agent.name}</p>
        <p className="text-[11px] text-[#8A7355] mt-0.5">{agent.role}</p>
      </div>

      {/* Status pill */}
      <div className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-all ${
        done
          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
          : progress > 0
          ? "border-[rgba(0,0,0,0.10)] text-[#4A3B1E]"
          : "bg-[#F9F6EF] text-[#8A7355] border-[#E8E0CE]"
      }`}
        style={!done && progress > 0 ? { background: `${agent.bgLight}`, borderColor: `${agent.color}30` } : {}}
      >
        {done ? "Complete" : progress > 0 ? `${progress}%` : "Waiting"}
      </div>

      {/* Current task */}
      <p className="text-[11px] text-[#8A7355] min-h-[28px] leading-snug px-1">
        {done ? "✓ Analysis done" : progress > 0 ? agent.tasks[Math.min(taskIndex, agent.tasks.length - 1)] : "—"}
      </p>
    </motion.div>
  );
}

// ─── Main onboarding page ─────────────────────────────────
export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);

  // Step 1 state
  const [company, setCompany] = useState<CompanyForm>({
    legalName: "", industry: "", jurisdiction: "", address: "",
    email: "", phone: "", insurerName: "", policyNumber: "", coverage: "",
    signatories: [{ name: "", role: "" }],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Step 2 state
  const [contracts, setContracts] = useState<ContractFile[]>([]);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Step 3 – agent run state
  const [agentStates, setAgentStates] = useState(
    AGENTS.map(() => ({ progress: 0, taskIndex: 0, done: false }))
  );
  const [runLog, setRunLog] = useState<{ time: string; agent: string; msg: string; color: string }[]>([]);
  const [runDone, setRunDone] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  // ── Validation ──
  const validateStep1 = () => {
    const e: Record<string, string> = {};
    if (!company.legalName.trim())  e.legalName   = "Required";
    if (!company.industry)          e.industry    = "Required";
    if (!company.jurisdiction.trim()) e.jurisdiction = "Required";
    if (!company.email.trim())      e.email       = "Required";
    if (company.signatories.every(s => !s.name.trim())) e.signatories = "Add at least one signatory";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const validateStep2 = () => {
    if (contracts.length === 0) {
      setErrors({ contracts: "Upload at least one contract file" });
      return false;
    }
    return true;
  };

  // ── File handling ──
  const readFile = (f: File) => {
    if (!f.name.endsWith(".txt") && !f.name.endsWith(".pdf")) {
      setErrors({ contracts: "Only .txt files supported" });
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      setContracts(prev => [...prev, {
        name: f.name,
        label: f.name.replace(/\.(txt|pdf)$/, ""),
        content: ev.target?.result as string,
        size: f.size,
      }]);
      setErrors({});
    };
    reader.readAsText(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    Array.from(e.dataTransfer.files).forEach(readFile);
  }, []);

  // ── Agent simulation ──
  const pushLog = (agent: string, msg: string, color: string) => {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    setRunLog(prev => [...prev.slice(-80), { time, agent, msg, color }]);
    setTimeout(() => logRef.current?.scrollTo({ top: 99999, behavior: "smooth" }), 50);
  };

  const runAgents = async () => {
    setStep(3);
    setRunDone(false);
    setRunLog([]);
    setAgentStates(AGENTS.map(() => ({ progress: 0, taskIndex: 0, done: false })));

    const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

    for (let ai = 0; ai < AGENTS.length; ai++) {
      const ag = AGENTS[ai];
      pushLog(ag.name, `Starting ${ag.role.toLowerCase()}…`, ag.color);
      for (let p = 0; p <= 100; p += 20) {
        setAgentStates(prev => prev.map((s, i) =>
          i === ai ? { ...s, progress: p, taskIndex: Math.floor(p / 20) } : s
        ));
        const taskIdx = Math.min(Math.floor(p / 20), ag.tasks.length - 1);
        if (p > 0) pushLog(ag.name, ag.tasks[taskIdx], ag.color);
        await delay(300 + Math.random() * 200);
      }
      setAgentStates(prev => prev.map((s, i) => i === ai ? { progress: 100, taskIndex: 4, done: true } : s));
      pushLog(ag.name, `✓ Complete`, ag.color);
      await delay(200);
    }
    setRunDone(true);
    pushLog("System", `Analysis complete — ${contracts.length} contracts processed`, "#10B981");
  };

  // ── Signatories helpers ──
  const addSignatory = () => setCompany(c => ({ ...c, signatories: [...c.signatories, { name: "", role: "" }] }));
  const removeSignatory = (i: number) => setCompany(c => ({ ...c, signatories: c.signatories.filter((_, idx) => idx !== i) }));
  const setSignatory = (i: number, k: keyof Signatory, v: string) =>
    setCompany(c => ({ ...c, signatories: c.signatories.map((s, idx) => idx === i ? { ...s, [k]: v } : s) }));

  const setField = (k: keyof Omit<CompanyForm, "signatories">) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setCompany(c => ({ ...c, [k]: e.target.value }));

  // ────────────────────────────────────────────────────────
  return (
    <div className="min-h-dvh bg-page flex flex-col">
      {/* Top bar */}
      <header className="bg-header border-b border-white/[0.06] px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
            <Scale className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white text-sm tracking-wide">ODIN</span>
          <span className="text-white/30 text-sm">·</span>
          <span className="text-white/50 text-sm">Contract Intelligence</span>
        </div>
        <div className="flex items-center gap-3">
          {step < 3 && (
            <button
              onClick={() => router.push("/war-room")}
              className="text-white/40 hover:text-white/70 text-sm transition-colors"
            >
              Skip → Dashboard
            </button>
          )}
          <button
            onClick={() => router.push("/login")}
            className="text-amber-400/90 hover:text-amber-300 text-xs font-semibold px-2.5 py-1 rounded border border-amber-500/30 bg-amber-500/10 transition-colors"
          >
            Sign In
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-5 py-12">
        <AnimatePresence mode="wait">

          {/* ═══ STEP 1 — Company Details ═══ */}
          {step === 1 && (
            <motion.div key="step1"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.3, ease: [0.16,1,0.3,1] }}
            >
              <StepBar step={1} />

              <div className="mb-8">
                <h1 className="heading-xl">Register your company</h1>
                <p className="text-[#8A7355] mt-1.5 text-sm">
                  This information lets our agents understand your legal entity and obligations.
                </p>
              </div>

              <div className="space-y-6">
                {/* Company basics */}
                <div className="card p-6 space-y-4">
                  <p className="font-semibold text-[#1A1208] text-sm flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-amber-600" /> Company Information
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="sm:col-span-2">
                      <label className="input-label">Legal Entity Name *</label>
                      <input className={`input-field ${errors.legalName ? "!border-red-400" : ""}`}
                        placeholder="e.g. Quillhub Inc." value={company.legalName} onChange={setField("legalName")} />
                      {errors.legalName && <p className="text-red-500 text-xs mt-1">{errors.legalName}</p>}
                    </div>
                    <div>
                      <label className="input-label">Industry *</label>
                      <select className={`input-field ${errors.industry ? "!border-red-400" : ""}`}
                        value={company.industry} onChange={setField("industry")}>
                        <option value="">Select industry…</option>
                        {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                      </select>
                      {errors.industry && <p className="text-red-500 text-xs mt-1">{errors.industry}</p>}
                    </div>
                    <div>
                      <label className="input-label">Jurisdiction *</label>
                      <input className={`input-field ${errors.jurisdiction ? "!border-red-400" : ""}`}
                        placeholder="e.g. Delaware, USA" value={company.jurisdiction} onChange={setField("jurisdiction")} />
                      {errors.jurisdiction && <p className="text-red-500 text-xs mt-1">{errors.jurisdiction}</p>}
                    </div>
                    <div className="sm:col-span-2">
                      <label className="input-label">Registered Address</label>
                      <input className="input-field" placeholder="Street, City, State, ZIP"
                        value={company.address} onChange={setField("address")} />
                    </div>
                    <div>
                      <label className="input-label">Legal Notice Email *</label>
                      <input type="email" className={`input-field ${errors.email ? "!border-red-400" : ""}`}
                        placeholder="legal@company.com" value={company.email} onChange={setField("email")} />
                      {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
                    </div>
                    <div>
                      <label className="input-label">Phone (optional)</label>
                      <input type="tel" className="input-field" placeholder="+1 (555) 000-0000"
                        value={company.phone} onChange={setField("phone")} />
                    </div>
                  </div>
                </div>

                {/* Signatories */}
                <div className="card p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-[#1A1208] text-sm flex items-center gap-2">
                      <User className="w-4 h-4 text-amber-600" /> Authorized Signatories
                    </p>
                    <button onClick={addSignatory} className="btn-ghost text-xs py-1.5 px-3 gap-1">
                      <Plus className="w-3.5 h-3.5" /> Add
                    </button>
                  </div>
                  {errors.signatories && <p className="text-red-500 text-xs">{errors.signatories}</p>}
                  <div className="space-y-3">
                    {company.signatories.map((s, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <input className="input-field" placeholder="Full name"
                          value={s.name} onChange={e => setSignatory(i, "name", e.target.value)} />
                        <input className="input-field" placeholder="Title / Role"
                          value={s.role} onChange={e => setSignatory(i, "role", e.target.value)} />
                        {company.signatories.length > 1 && (
                          <button onClick={() => removeSignatory(i)}
                            className="p-2 rounded-lg text-[#8A7355] hover:text-red-500 hover:bg-red-50 transition-colors shrink-0">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Insurance */}
                <div className="card p-6 space-y-4">
                  <p className="font-semibold text-[#1A1208] text-sm flex items-center gap-2">
                    <Shield className="w-4 h-4 text-amber-600" /> Insurance Policy <span className="text-[#8A7355] font-normal text-xs">(optional)</span>
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="input-label">Insurer Name</label>
                      <input className="input-field" placeholder="e.g. Chubb"
                        value={company.insurerName} onChange={setField("insurerName")} />
                    </div>
                    <div>
                      <label className="input-label">Policy Number</label>
                      <input className="input-field font-jetbrains" placeholder="POL-2026-XXX"
                        value={company.policyNumber} onChange={setField("policyNumber")} />
                    </div>
                    <div>
                      <label className="input-label">Coverage Limit</label>
                      <input className="input-field" placeholder="$500,000"
                        value={company.coverage} onChange={setField("coverage")} />
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end mt-8">
                <button onClick={() => { if (validateStep1()) setStep(2); }} className="btn-primary gap-2 px-8 py-3 text-[15px]">
                  Continue <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {/* ═══ STEP 2 — Upload Contracts ═══ */}
          {step === 2 && (
            <motion.div key="step2"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.3, ease: [0.16,1,0.3,1] }}
            >
              <StepBar step={2} />

              <div className="mb-8">
                <h1 className="heading-xl">Upload your contracts</h1>
                <p className="text-[#8A7355] mt-1.5 text-sm">
                  Upload the contract files you want analyzed. Supports plain text (.txt) files.
                </p>
              </div>

              <div className="space-y-5">
                {/* Dropzone */}
                <div
                  className={`dropzone ${dragging ? "active" : ""} ${errors.contracts ? "!border-red-400" : ""}`}
                  onClick={() => fileRef.current?.click()}
                  onDragOver={e => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                >
                  <input ref={fileRef} type="file" accept=".txt" multiple className="hidden"
                    onChange={e => { Array.from(e.target.files || []).forEach(readFile); }} />
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-14 h-14 rounded-full bg-[#F2EDE1] flex items-center justify-center">
                      <Upload className="w-6 h-6 text-[#D4A017]" />
                    </div>
                    <div>
                      <p className="font-semibold text-[#1A1208]">
                        Drag & drop files or <span className="text-amber-600 underline underline-offset-2 cursor-pointer">browse</span>
                      </p>
                      <p className="text-sm text-[#8A7355] mt-1">Plain text (.txt) contracts · Multiple files allowed</p>
                    </div>
                  </div>
                </div>
                {errors.contracts && (
                  <p className="flex items-center gap-1.5 text-red-500 text-sm">
                    <AlertCircle className="w-4 h-4" />{errors.contracts}
                  </p>
                )}

                {/* File list */}
                {contracts.length > 0 && (
                  <div className="card overflow-hidden">
                    <div className="px-5 py-3 border-b border-[rgba(212,160,23,0.12)] bg-[#FEFAF3]">
                      <p className="font-semibold text-[#1A1208] text-sm">
                        {contracts.length} file{contracts.length !== 1 ? "s" : ""} queued
                      </p>
                    </div>
                    <div className="divide-y divide-[rgba(26,18,8,0.05)]">
                      {contracts.map((c, i) => (
                        <div key={i} className="flex items-center gap-4 px-5 py-3.5 hover:bg-[#FEFAF3] transition-colors">
                          <div className="w-9 h-9 rounded-lg bg-[#F2EDE1] flex items-center justify-center shrink-0">
                            <FileText className="w-4 h-4 text-amber-700" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <input
                              className="font-medium text-sm text-[#1A1208] bg-transparent border-none outline-none w-full"
                              value={c.label}
                              onChange={e => setContracts(prev => prev.map((f, idx) => idx === i ? { ...f, label: e.target.value } : f))}
                              placeholder="Contract label…"
                            />
                            <p className="text-xs text-[#8A7355] mt-0.5">{c.name} · {(c.size / 1024).toFixed(1)} KB</p>
                          </div>
                          <div className="badge badge-green text-[11px] shrink-0">Ready</div>
                          <button
                            onClick={() => setContracts(prev => prev.filter((_, idx) => idx !== i))}
                            className="p-1.5 rounded-lg text-[#8A7355] hover:text-red-500 hover:bg-red-50 transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Summary card */}
                {company.legalName && (
                  <div className="card-gold p-4 flex items-center gap-4 rounded-xl">
                    <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center shrink-0">
                      <Building2 className="w-5 h-5 text-amber-700" />
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-[#1A1208] text-sm">{company.legalName}</p>
                      <p className="text-xs text-[#8A7355] mt-0.5">{company.industry} · {company.jurisdiction}</p>
                    </div>
                    <div className="badge badge-gold">{company.signatories.filter(s => s.name).length} signator{company.signatories.filter(s=>s.name).length===1?"y":"ies"}</div>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mt-8">
                <button onClick={() => setStep(1)} className="btn-ghost gap-2">
                  ← Back
                </button>
                <button
                  onClick={() => { if (validateStep2()) runAgents(); }}
                  className="btn-primary gap-2 px-8 py-3 text-[15px]"
                >
                  <Zap className="w-4 h-4" />
                  Run Analysis
                </button>
              </div>
            </motion.div>
          )}

          {/* ═══ STEP 3 — Agent Processing ═══ */}
          {step === 3 && (
            <motion.div key="step3"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: [0.16,1,0.3,1] }}
              className="max-w-4xl mx-auto w-full"
            >
              <StepBar step={3} />

              <div className="mb-8 flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <h1 className="heading-xl">
                    {runDone ? "Analysis complete" : "Analyzing contracts…"}
                  </h1>
                  <p className="text-[#8A7355] mt-1.5 text-sm">
                    {runDone
                      ? `${contracts.length} contract${contracts.length!==1?"s":""} processed for ${company.legalName}.`
                      : "Our agents are reading, extracting and cross-referencing your contracts."
                    }
                  </p>
                </div>

                {runDone && (
                  <motion.button
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    onClick={() => router.push("/war-room")}
                    className="btn-primary gap-2 px-6 py-2.5 shrink-0"
                  >
                    View Dashboard <ArrowRight className="w-4 h-4" />
                  </motion.button>
                )}
              </div>

              {/* Agent grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
                {AGENTS.map((ag, i) => (
                  <AgentCard
                    key={ag.id}
                    agent={ag}
                    progress={agentStates[i].progress}
                    taskIndex={agentStates[i].taskIndex}
                    done={agentStates[i].done}
                  />
                ))}
              </div>

              {/* Progress bar */}
              <div className="card p-4 mb-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-[#1A1208]">Overall Progress</p>
                  <p className="text-sm font-mono text-[#8A7355]">
                    {Math.round(agentStates.reduce((s, a) => s + a.progress, 0) / AGENTS.length)}%
                  </p>
                </div>
                <div className="h-2 bg-[#F2EDE1] rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-600"
                    animate={{ width: `${Math.round(agentStates.reduce((s,a)=>s+a.progress,0)/AGENTS.length)}%` }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                  />
                </div>
              </div>

              {/* Live log */}
              <div className="card overflow-hidden">
                <div className="px-4 py-3 border-b border-[rgba(212,160,23,0.12)] bg-[#FEFAF3] flex items-center gap-2">
                  <div className={`status-dot ${runDone ? "dot-green" : "dot-gold pulse-dot"}`} />
                  <p className="text-sm font-semibold text-[#1A1208]">Live Activity Log</p>
                </div>
                <div ref={logRef} className="h-44 overflow-y-auto p-4 font-jetbrains text-xs space-y-1 bg-[#FEFBF3]">
                  <AnimatePresence initial={false}>
                    {runLog.map((l, i) => (
                      <motion.div key={i}
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="flex items-baseline gap-2"
                      >
                        <span className="text-[#8A7355] shrink-0">{l.time}</span>
                        <span className="font-bold shrink-0" style={{ color: l.color }}>{l.agent}</span>
                        <span className="text-[#4A3B1E]">{l.msg}</span>
                      </motion.div>
                    ))}
                    {runLog.length === 0 && (
                      <p className="text-[#8A7355] italic">Waiting for agents to start…</p>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  );
}