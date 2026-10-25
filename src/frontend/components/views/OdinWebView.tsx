"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  FileText,
  Upload,
  Play,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  ExternalLink,
  Layers,
  ShieldAlert,
  Zap,
  ArrowRight,
  Eye,
  FileSearch,
  Check,
  Clock,
  ChevronRight,
  Sparkles,
  Brain,
} from "lucide-react";
import { AgentMemoryMap } from "./AgentMemoryMap";

interface ContractItem {
  id: string;
  document_key: string;
  title: string;
  status: string;
  severity: string;
  next_deadline: string | null;
  last_analyzed: string | null;
  content_sha256: string;
  source: string;
}

interface ContractDetail extends ContractItem {
  content?: string;
  pages?: number;
  clauses?: { id: string; title: string; text: string; offset: number }[];
}

interface AgentRun {
  id: string;
  status: string;
  created_at: string;
  findings?: { claim: string; explanation: string; severity: string; status: string }[];
}

export function OdinWebView() {
  const [contracts, setContracts] = useState<ContractItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<ContractDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Upload state
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Agent execution state
  const [runningAgent, setRunningAgent] = useState<boolean>(false);
  const [agentResult, setAgentResult] = useState<string | null>(null);

  // Active sub-view
  const [activeTab, setActiveTab] = useState<"contracts" | "memory_map" | "council">("contracts");

  // Fetch contracts
  const fetchContracts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = typeof window !== "undefined" ? localStorage.getItem("odin_token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/v1/workspace/contracts", { headers });
      if (!res.ok) {
        throw new Error(`Failed to load contracts: HTTP ${res.status}`);
      }
      const data = await res.json();
      setContracts(data.items || []);
    } catch (err: any) {
      setError(err?.message || "Could not connect to Odin API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchContracts();
  }, [fetchContracts]);

  // Load contract details when a contract is selected
  const viewContractDetail = async (key: string) => {
    try {
      setSelectedKey(key);
      setLoadingDetail(true);
      const token = typeof window !== "undefined" ? localStorage.getItem("odin_token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/v1/workspace/contracts/${encodeURIComponent(key)}`, { headers });
      if (res.ok) {
        const detail = await res.json();
        setSelectedDetail(detail);
      }
    } catch {
      // ignore
    } finally {
      setLoadingDetail(false);
    }
  };

  // Upload handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      setUploadSuccess(null);
      setError(null);

      const formData = new FormData();
      formData.append("file", file);

      const token = typeof window !== "undefined" ? localStorage.getItem("odin_token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/v1/workspace/upload-file", {
        method: "POST",
        body: formData,
        headers,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Upload failed with status ${res.status}`);
      }

      const result = await res.json();
      setUploadSuccess(`Successfully ingested "${result.title || file.name}" (${result.pages || 1} pages OCR-indexed).`);
      fetchContracts();
    } catch (err: any) {
      setError(err?.message || "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Run ODIN intelligence agent pipeline
  const handleRunAgents = async (keys: string[]) => {
    if (!keys.length) return;
    try {
      setRunningAgent(true);
      setAgentResult(null);

      const token = typeof window !== "undefined" ? localStorage.getItem("odin_token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/v1/workspace/agents/runs", {
        method: "POST",
        headers,
        body: JSON.stringify({ document_keys: keys }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Agent execution failed");
      }

      const run = await res.json();
      setAgentResult(`Agent run started successfully (Run ID: ${run.id || "Active"}). Agents Thor, Heimdall, Loki, Tyr, and Norns are analyzing.`);
    } catch (err: any) {
      setError(err?.message || "Failed to trigger agent run");
    } finally {
      setRunningAgent(false);
    }
  };

  const filteredContracts = contracts.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.document_key.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Top Banner / Telemetry */}
      <div className="bg-white border border-[#E8E1D5] rounded-xl p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-amber-800">
              Odin Web &middot; Live OCR &amp; Intelligence Workspace
            </span>
          </div>
          <h1 className="text-2xl font-bold text-[#17375B] mt-1">
            Institutional Document Vault &amp; Agent Feeder
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Synchronized with local backend API at <code className="font-mono bg-amber-50 text-amber-900 px-1.5 py-0.5 rounded text-xs">http://127.0.0.1:8000</code>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.txt,.png,.jpg,.jpeg,.webp"
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#17375B] hover:bg-[#1f497a] text-white font-medium text-xs transition-colors shadow-xs"
          >
            {uploading ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Upload className="w-3.5 h-3.5" />
            )}
            {uploading ? "Extracting OCR..." : "Upload Contract / PDF"}
          </button>

          <button
            onClick={() => fetchContracts()}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#E8E1D5] bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
            Refresh
          </button>
        </div>
      </div>

      {/* Upload success feedback */}
      {uploadSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-lg text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
          <button onClick={() => setUploadSuccess(null)} className="text-emerald-700 font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Error alert */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-lg text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-700 font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-[#E8E1D5] rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Ingested Contracts</span>
          <div className="text-2xl font-bold font-mono text-[#17375B] mt-1">{contracts.length}</div>
          <span className="text-[11px] text-slate-400">Vault SQLite store</span>
        </div>

        <div className="bg-white border border-[#E8E1D5] rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">OCR Engine</span>
          <div className="text-2xl font-bold text-emerald-700 mt-1">PyMuPDF + EasyOCR</div>
          <span className="text-[11px] text-emerald-600 font-mono">Zero-loss page extraction</span>
        </div>

        <div className="bg-white border border-[#E8E1D5] rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Thor Sub-Agent</span>
          <div className="text-2xl font-bold text-amber-700 mt-1">Active / Connected</div>
          <span className="text-[11px] text-amber-700 font-mono">SSE Stream on :8000/thor</span>
        </div>

        <div className="bg-white border border-[#E8E1D5] rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pipeline Readiness</span>
          <div className="text-2xl font-bold text-slate-800 mt-1">100% Ready</div>
          <span className="text-[11px] text-slate-400">Thor &middot; Heimdall &middot; Loki &middot; Tyr</span>
        </div>
      </div>

      {/* Tab Nav */}
      <div className="flex items-center gap-2 border-b border-[#E8E1D5] pb-2">
        <button
          onClick={() => setActiveTab("contracts")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === "contracts"
              ? "bg-[#17375B] text-white"
              : "text-slate-600 hover:text-slate-900 hover:bg-white"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Contract Vault ({contracts.length})
        </button>

        <button
          onClick={() => setActiveTab("memory_map")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === "memory_map"
              ? "bg-[#17375B] text-white"
              : "text-slate-600 hover:text-slate-900 hover:bg-white"
          }`}
        >
          <Brain className="w-3.5 h-3.5 text-amber-500" />
          Shared Memory Map (2D Vector Space)
        </button>

        <button
          onClick={() => setActiveTab("council")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === "council"
              ? "bg-[#17375B] text-white"
              : "text-slate-600 hover:text-slate-900 hover:bg-white"
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          Council Dispatch
        </button>
      </div>

      {/* TAB 1: CONTRACT VAULT */}
      {activeTab === "contracts" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Contract List */}
          <div className="lg:col-span-7 bg-white border border-[#E8E1D5] rounded-xl shadow-xs p-5 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter contracts by title or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-[#E8E1D5] rounded-lg text-slate-900 focus:outline-hidden focus:border-[#17375B]"
                />
              </div>
              <span className="text-[11px] font-mono text-slate-500 shrink-0">
                {filteredContracts.length} document(s)
              </span>
            </div>

            {loading ? (
              <div className="py-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-amber-600" />
                Loading ingested documents from database...
              </div>
            ) : filteredContracts.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No matching contracts found.
              </div>
            ) : (
              <div className="divide-y divide-[#E8E1D5] overflow-hidden rounded-lg border border-[#E8E1D5]">
                {filteredContracts.map((c) => {
                  const isSelected = selectedKey === c.document_key;
                  return (
                    <div
                      key={c.id || c.document_key}
                      onClick={() => viewContractDetail(c.document_key)}
                      className={`p-3.5 flex items-center justify-between gap-3 cursor-pointer transition-colors ${
                        isSelected ? "bg-amber-50/60" : "hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 text-slate-600">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs text-[#17375B] truncate">
                              {c.title}
                            </span>
                            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 shrink-0">
                              {c.document_key}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-0.5 font-mono">
                            <span>source: {c.source || "pdf"}</span>
                            <span>sha: {c.content_sha256?.slice(0, 10)}&hellip;</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <a
                          href={`/api/v1/workspace/contracts/${encodeURIComponent(c.document_key)}/source`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="px-2 py-1 rounded border border-[#E8E1D5] text-[11px] text-slate-600 hover:text-slate-900 hover:bg-white flex items-center gap-1"
                        >
                          <ExternalLink className="w-3 h-3" />
                          Source
                        </a>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRunAgents([c.document_key]);
                          }}
                          disabled={runningAgent}
                          className="px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold text-[11px] flex items-center gap-1 shadow-xs"
                        >
                          <Play className="w-3 h-3 fill-slate-900" />
                          Analyze
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Contract Detail Panel */}
          <div className="lg:col-span-5 bg-white border border-[#E8E1D5] rounded-xl shadow-xs p-5 space-y-4">
            <h3 className="font-bold text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-amber-600" />
              Document Inspector
            </h3>

            {!selectedKey ? (
              <div className="py-20 text-center text-slate-400 text-xs">
                Select any contract from the vault to inspect its OCR-extracted text and clause structure.
              </div>
            ) : loadingDetail ? (
              <div className="py-20 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-amber-600" />
                Loading contract content...
              </div>
            ) : selectedDetail ? (
              <div className="space-y-3">
                <div className="p-3 bg-slate-50 rounded-lg border border-[#E8E1D5] space-y-1">
                  <div className="font-semibold text-xs text-[#17375B]">
                    {selectedDetail.title}
                  </div>
                  <div className="text-[11px] font-mono text-slate-500 flex items-center gap-3">
                    <span>Key: {selectedDetail.document_key}</span>
                    <span>Format: {selectedDetail.source}</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-600">Extracted Content Preview:</span>
                  <div className="p-3 bg-slate-900 text-slate-200 font-mono text-[11px] rounded-lg max-h-80 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                    {selectedDetail.content || "Content loaded in memory."}
                  </div>
                </div>

                <div className="pt-2 flex items-center gap-2">
                  <a
                    href={`/api/v1/workspace/contracts/${encodeURIComponent(selectedDetail.document_key)}/source`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 text-center py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-xs transition-colors flex items-center justify-center gap-1.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Open Source Document
                  </a>
                  <button
                    onClick={() => handleRunAgents([selectedDetail.document_key])}
                    disabled={runningAgent}
                    className="flex-1 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold text-xs transition-colors flex items-center justify-center gap-1.5 shadow-xs"
                  >
                    <Play className="w-3.5 h-3.5 fill-slate-900" />
                    Run Agent Pipeline
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* TAB 2: COUNCIL DISPATCH */}
      {activeTab === "council" && (
        <div className="bg-white border border-[#E8E1D5] rounded-xl shadow-xs p-6 space-y-6">
          <div>
            <h2 className="text-lg font-bold text-[#17375B]">
              Multi-Agent Council Dispatch
            </h2>
            <p className="text-xs text-slate-600 mt-1">
              Select contracts from the vault to initiate autonomous multi-agent analysis through Thor &rarr; Heimdall &rarr; Loki &rarr; Tyr &rarr; Norns.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            {[
              { name: "Thor", role: "OCR & Facts Extractor", color: "bg-cyan-50 border-cyan-200 text-cyan-900" },
              { name: "Heimdall", role: "Event Proof Verifier", color: "bg-emerald-50 border-emerald-200 text-emerald-900" },
              { name: "Norns", role: "Scenario Forecaster", color: "bg-amber-50 border-amber-200 text-amber-900" },
              { name: "Loki", role: "Adversarial Challenger", color: "bg-purple-50 border-purple-200 text-purple-900" },
              { name: "Tyr", role: "Adjudication & Action", color: "bg-rose-50 border-rose-200 text-rose-900" },
            ].map((agent) => (
              <div key={agent.name} className={`p-3 rounded-lg border ${agent.color}`}>
                <div className="font-bold text-xs">{agent.name}</div>
                <div className="text-[10px] opacity-80 mt-0.5">{agent.role}</div>
              </div>
            ))}
          </div>

          <div className="p-4 bg-slate-50 border border-[#E8E1D5] rounded-lg space-y-3">
            <div className="font-semibold text-xs text-slate-700">Quick Actions</div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleRunAgents(["A1", "A2", "A3"])}
                disabled={runningAgent}
                className="px-3 py-1.5 rounded bg-white border border-[#E8E1D5] hover:border-slate-400 text-xs font-medium text-slate-800 flex items-center gap-1.5 shadow-xs"
              >
                <Play className="w-3 h-3 text-amber-600" />
                Analyze StratoNode Cluster (A1 + A2 + A3)
              </button>
              <button
                onClick={() => handleRunAgents(["B1", "B2"])}
                disabled={runningAgent}
                className="px-3 py-1.5 rounded bg-white border border-[#E8E1D5] hover:border-slate-400 text-xs font-medium text-slate-800 flex items-center gap-1.5 shadow-xs"
              >
                <Play className="w-3 h-3 text-amber-600" />
                Analyze Harbor Retail (B1 + B2)
              </button>
              <button
                onClick={() => handleRunAgents(["STD"])}
                disabled={runningAgent}
                className="px-3 py-1.5 rounded bg-white border border-[#E8E1D5] hover:border-slate-400 text-xs font-medium text-slate-800 flex items-center gap-1.5 shadow-xs"
              >
                <Play className="w-3 h-3 text-amber-600" />
                Analyze Standard Terms (STD)
              </button>
            </div>
          </div>

          {agentResult && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{agentResult}</span>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: SHARED MEMORY MAP */}
      {activeTab === "memory_map" && <AgentMemoryMap />}
    </div>
  );
}
