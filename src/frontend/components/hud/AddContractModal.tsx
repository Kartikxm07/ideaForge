"use client";

import React, { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Upload,
  FileText,
  Building2,
  User,
  Mail,
  Calendar,
  Tag,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";

interface AddContractModalProps {
  open: boolean;
  onClose: () => void;
  onAdd?: (contract: ContractDraft) => void;
}

export interface ContractDraft {
  id: string;
  companyName: string;
  counterparty: string;
  contactEmail: string;
  contractType: string;
  effectiveDate: string;
  expiryDate: string;
  notes: string;
  fileName: string;
  fileContent: string;
}

const CONTRACT_TYPES = [
  "Hosting & Infrastructure",
  "SLA / Service Agreement",
  "Customer Agreement",
  "Vendor / Contractor",
  "NDA / Confidentiality",
  "Amendment / Addendum",
  "Master Services Agreement",
  "Other",
];

export function AddContractModal({ open, onClose, onAdd }: AddContractModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    companyName: "",
    counterparty: "",
    contactEmail: "",
    contractType: "",
    effectiveDate: "",
    expiryDate: "",
    notes: "",
  });
  const [file, setFile] = useState<{ name: string; content: string } | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const readFile = (f: File) => {
    if (!f.name.endsWith(".txt")) {
      setErrors((e) => ({ ...e, file: "Only .txt files are supported." }));
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      setFile({ name: f.name, content: ev.target?.result as string });
      setErrors((e) => { const n = { ...e }; delete n.file; return n; });
    };
    reader.readAsText(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) readFile(f);
  }, []);

  const validateStep1 = () => {
    const e: Record<string, string> = {};
    if (!form.companyName.trim())  e.companyName  = "Company name is required";
    if (!form.counterparty.trim()) e.counterparty = "Counterparty is required";
    if (!form.contractType)        e.contractType = "Select a contract type";
    if (!form.effectiveDate)       e.effectiveDate = "Effective date is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleNext = () => {
    if (validateStep1()) setStep(2);
  };

  const handleSubmit = async () => {
    const e: Record<string, string> = {};
    if (!file) e.file = "Please upload a .txt contract file";
    setErrors(e);
    if (Object.keys(e).length > 0) return;

    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 1400));
    setSubmitting(false);
    setSubmitted(true);

    onAdd?.({
      id: `CTR-${Date.now()}`,
      ...form,
      fileName: file!.name,
      fileContent: file!.content,
    });

    await new Promise((r) => setTimeout(r, 1200));
    handleClose();
  };

  const handleClose = () => {
    setStep(1);
    setSubmitted(false);
    setSubmitting(false);
    setFile(null);
    setErrors({});
    setForm({ companyName: "", counterparty: "", contactEmail: "", contractType: "", effectiveDate: "", expiryDate: "", notes: "" });
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="modal-overlay" onClick={handleClose}>
          <motion.div
            className="modal-panel"
            onClick={(e) => e.stopPropagation()}
            initial={{ opacity: 0, scale: 0.96, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 16 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            {/* Header */}
            <div className="modal-header">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-md shadow-amber-500/25">
                  <FileText className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 className="font-bold text-[#1A1208] text-base leading-tight">Add Contract</h2>
                  <p className="text-[11px] text-[#8A7355] mt-0.5">
                    Step {step} of 2 — {step === 1 ? "Contract Details" : "Upload File"}
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="w-8 h-8 rounded-lg hover:bg-[#1A1208]/06 flex items-center justify-center text-[#8A7355] hover:text-[#1A1208] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Step progress bar */}
            <div className="h-0.5 bg-[#F2EDE1]">
              <motion.div
                className="h-full bg-gradient-to-r from-amber-400 to-amber-600"
                animate={{ width: step === 1 ? "50%" : "100%" }}
                transition={{ duration: 0.4, ease: "easeInOut" }}
              />
            </div>

            {/* Body */}
            <div className="p-6">
              <AnimatePresence mode="wait">
                {/* ─── STEP 1: Details ─── */}
                {step === 1 && (
                  <motion.div
                    key="step1"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-4"
                  >
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Company Name */}
                      <div>
                        <label className="input-label">
                          <Building2 className="w-3 h-3 inline mr-1" />
                          Your Company Name *
                        </label>
                        <input
                          className={`input-field ${errors.companyName ? "!border-red-400" : ""}`}
                          placeholder="e.g. Quillhub Inc."
                          value={form.companyName}
                          onChange={set("companyName")}
                        />
                        {errors.companyName && <p className="text-red-500 text-xs mt-1">{errors.companyName}</p>}
                      </div>

                      {/* Counterparty */}
                      <div>
                        <label className="input-label">
                          <User className="w-3 h-3 inline mr-1" />
                          Counterparty *
                        </label>
                        <input
                          className={`input-field ${errors.counterparty ? "!border-red-400" : ""}`}
                          placeholder="e.g. StratoNode LLC"
                          value={form.counterparty}
                          onChange={set("counterparty")}
                        />
                        {errors.counterparty && <p className="text-red-500 text-xs mt-1">{errors.counterparty}</p>}
                      </div>

                      {/* Contract Type */}
                      <div>
                        <label className="input-label">
                          <Tag className="w-3 h-3 inline mr-1" />
                          Contract Type *
                        </label>
                        <select
                          className={`input-field ${errors.contractType ? "!border-red-400" : ""}`}
                          value={form.contractType}
                          onChange={(e) => setForm((f) => ({ ...f, contractType: e.target.value }))}
                        >
                          <option value="">Select type…</option>
                          {CONTRACT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                        </select>
                        {errors.contractType && <p className="text-red-500 text-xs mt-1">{errors.contractType}</p>}
                      </div>

                      {/* Contact Email */}
                      <div>
                        <label className="input-label">
                          <Mail className="w-3 h-3 inline mr-1" />
                          Notice Email
                        </label>
                        <input
                          type="email"
                          className="input-field"
                          placeholder="legal@yourcompany.com"
                          value={form.contactEmail}
                          onChange={set("contactEmail")}
                        />
                      </div>

                      {/* Effective Date */}
                      <div>
                        <label className="input-label">
                          <Calendar className="w-3 h-3 inline mr-1" />
                          Effective Date *
                        </label>
                        <input
                          type="date"
                          className={`input-field ${errors.effectiveDate ? "!border-red-400" : ""}`}
                          value={form.effectiveDate}
                          onChange={set("effectiveDate")}
                        />
                        {errors.effectiveDate && <p className="text-red-500 text-xs mt-1">{errors.effectiveDate}</p>}
                      </div>

                      {/* Expiry Date */}
                      <div>
                        <label className="input-label">
                          <Calendar className="w-3 h-3 inline mr-1" />
                          Expiry Date
                        </label>
                        <input
                          type="date"
                          className="input-field"
                          value={form.expiryDate}
                          onChange={set("expiryDate")}
                        />
                      </div>
                    </div>

                    {/* Notes */}
                    <div>
                      <label className="input-label">Notes / Context</label>
                      <textarea
                        className="input-field min-h-[80px] resize-y"
                        placeholder="Any key context, clause flags, or risk notes…"
                        value={form.notes}
                        onChange={set("notes")}
                      />
                    </div>
                  </motion.div>
                )}

                {/* ─── STEP 2: File Upload ─── */}
                {step === 2 && (
                  <motion.div
                    key="step2"
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-4"
                  >
                    {/* Summary chip */}
                    <div className="flex items-center gap-2 p-3 bg-[#F9F6EF] rounded-lg border border-[rgba(212,160,23,0.20)]">
                      <Building2 className="w-4 h-4 text-amber-600 shrink-0" />
                      <div className="text-sm">
                        <span className="font-semibold text-[#1A1208]">{form.companyName}</span>
                        <span className="text-[#8A7355]"> → </span>
                        <span className="font-medium text-[#4A3B1E]">{form.counterparty}</span>
                        <span className="ml-2 badge badge-gold text-[11px]">{form.contractType}</span>
                      </div>
                    </div>

                    {/* Dropzone */}
                    <div
                      className={`dropzone ${dragging ? "active" : ""} ${errors.file ? "!border-red-400" : ""}`}
                      onClick={() => fileRef.current?.click()}
                      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                      onDragLeave={() => setDragging(false)}
                      onDrop={onDrop}
                    >
                      <input
                        ref={fileRef}
                        type="file"
                        accept=".txt"
                        className="hidden"
                        onChange={(e) => { const f = e.target.files?.[0]; if (f) readFile(f); }}
                      />
                      {file ? (
                        <div className="flex flex-col items-center gap-2">
                          <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                            <CheckCircle2 className="w-5 h-5 text-green-600" />
                          </div>
                          <p className="font-semibold text-[#1A1208] text-sm">{file.name}</p>
                          <p className="text-xs text-[#8A7355]">
                            {(file.content.length / 1024).toFixed(1)} KB — click to replace
                          </p>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center gap-2">
                          <div className="w-12 h-12 rounded-full bg-[#F2EDE1] flex items-center justify-center">
                            <Upload className="w-5 h-5 text-[#D4A017]" />
                          </div>
                          <p className="font-semibold text-[#1A1208] text-sm">
                            Drag & drop or <span className="text-amber-600 underline underline-offset-2">browse</span>
                          </p>
                          <p className="text-xs text-[#8A7355]">Supports .txt contract files only</p>
                        </div>
                      )}
                    </div>
                    {errors.file && (
                      <p className="flex items-center gap-1 text-red-500 text-xs">
                        <AlertCircle className="w-3.5 h-3.5" />{errors.file}
                      </p>
                    )}

                    {/* Preview snippet */}
                    {file && (
                      <div className="rounded-lg border border-[rgba(212,160,23,0.18)] bg-[#FEFAF3] p-3 max-h-32 overflow-y-auto">
                        <p className="label-caps mb-1.5">Preview</p>
                        <pre className="font-jetbrains text-[11px] text-[#4A3B1E] whitespace-pre-wrap leading-relaxed">
                          {file.content.slice(0, 600)}{file.content.length > 600 ? "…" : ""}
                        </pre>
                      </div>
                    )}

                    {/* Success flash */}
                    <AnimatePresence>
                      {submitted && (
                        <motion.div
                          initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                          className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg"
                        >
                          <CheckCircle2 className="w-4 h-4 text-green-600" />
                          <span className="text-sm font-medium text-green-700">Contract added successfully!</span>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="px-6 pb-6 flex items-center justify-between gap-3 pt-2 border-t border-[rgba(212,160,23,0.10)]">
              {step === 2 ? (
                <button onClick={() => setStep(1)} className="btn-ghost text-sm">
                  ← Back
                </button>
              ) : (
                <button onClick={handleClose} className="btn-ghost text-sm">
                  Cancel
                </button>
              )}

              {step === 1 ? (
                <button onClick={handleNext} className="btn-primary text-sm px-6">
                  Next: Upload File →
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={submitting || submitted}
                  className="btn-primary text-sm px-6 min-w-[140px]"
                >
                  {submitting ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</>
                  ) : submitted ? (
                    <><CheckCircle2 className="w-4 h-4" /> Added!</>
                  ) : (
                    "Add Contract"
                  )}
                </button>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
