"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Brain,
  Layers,
  Sparkles,
  Search,
  Filter,
  CheckCircle2,
  ExternalLink,
  Shield,
  Zap,
  Swords,
  Clock,
  UserCheck,
  RefreshCw,
  Maximize2,
  Activity,
  Cpu,
  Eye,
  Info,
} from "lucide-react";

interface FactItem {
  fact_type: string;
  value: string;
  confidence: number;
  status: string;
  quote: string;
}

interface MemoryNode {
  id: string;
  row_id: number;
  document_id: string;
  clause_ref: string;
  page_num: number;
  x: number;
  y: number;
  token_count: number;
  text_snippet: string;
  facts: FactItem[];
  has_claims: boolean;
}

interface MemoryEdge {
  source: string;
  target: string;
  kind: string;
  doc: string;
}

interface MemoryMapData {
  total_chunks: number;
  total_facts: number;
  embedding_dim: number;
  vector_store: string;
  dimensions: string[];
  nodes: MemoryNode[];
  edges: MemoryEdge[];
}

const DIMENSION_COLORS: Record<string, { bg: string; border: string; text: string; fill: string }> = {
  sla_tier: { bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-800", fill: "#10b981" },
  liability_caps: { bg: "bg-rose-50", border: "border-rose-300", text: "text-rose-800", fill: "#ef4444" },
  claim_windows: { bg: "bg-amber-50", border: "border-amber-300", text: "text-amber-800", fill: "#f59e0b" },
  notice_terms: { bg: "bg-cyan-50", border: "border-cyan-300", text: "text-cyan-800", fill: "#06b6d4" },
  parties: { bg: "bg-indigo-50", border: "border-indigo-300", text: "text-indigo-800", fill: "#6366f1" },
  termination: { bg: "bg-purple-50", border: "border-purple-300", text: "text-purple-800", fill: "#a855f7" },
  exclusivity: { bg: "bg-blue-50", border: "border-blue-300", text: "text-blue-800", fill: "#3b82f6" },
  general: { bg: "bg-slate-50", border: "border-slate-300", text: "text-slate-800", fill: "#64748b" },
};

export function AgentMemoryMap() {
  const [data, setData] = useState<MemoryMapData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedDimension, setSelectedDimension] = useState<string>("all");
  const [selectedDoc, setSelectedDoc] = useState<string>("all");
  const [claimsOnly, setClaimsOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Selected node for inspection
  const [selectedNode, setSelectedNode] = useState<MemoryNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<MemoryNode | null>(null);

  const fetchMemoryMap = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/thor/api/memory_map");
      if (!res.ok) {
        throw new Error(`Failed to load memory map: HTTP ${res.status}`);
      }
      const json: MemoryMapData = await res.json();
      setData(json);
      // Auto-select first node with claims
      const firstWithClaim = json.nodes.find((n) => n.has_claims);
      if (firstWithClaim) setSelectedNode(firstWithClaim);
    } catch (err: any) {
      setError(err?.message || "Failed to load agent shared memory map");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemoryMap();
  }, []);

  // Filtered nodes
  const filteredNodes = useMemo(() => {
    if (!data) return [];
    return data.nodes.filter((node) => {
      if (claimsOnly && !node.has_claims) return false;
      if (selectedDoc !== "all" && !node.document_id.includes(selectedDoc)) return false;
      if (selectedDimension !== "all") {
        if (!node.facts.some((f) => f.fact_type === selectedDimension)) return false;
      }
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchId = node.id.toLowerCase().includes(q);
        const matchText = node.text_snippet.toLowerCase().includes(q);
        const matchFact = node.facts.some(
          (f) => f.value.toLowerCase().includes(q) || f.quote.toLowerCase().includes(q)
        );
        if (!matchId && !matchText && !matchFact) return false;
      }
      return true;
    });
  }, [data, claimsOnly, selectedDoc, selectedDimension, searchQuery]);

  // Unique document IDs
  const docIds = useMemo(() => {
    if (!data) return [];
    const set = new Set<string>();
    data.nodes.forEach((n) => {
      const stem = n.document_id.split("/").pop()?.replace(".txt", "") || n.document_id;
      set.add(stem);
    });
    return Array.from(set).sort();
  }, [data]);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-[#E8E1D5] rounded-xl p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-pulse" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-800">
              Shared Council Memory Topology &middot; Thor Evidence Surface
            </span>
          </div>
          <h2 className="text-xl font-bold text-[#17375B] mt-1">
            2D Semantic Memory Map (128-Dim Vector Projection)
          </h2>
          <p className="text-xs text-slate-600 mt-0.5">
            Real-time memory substrate backing <strong>Thor</strong>, <strong>Heimdall</strong>, <strong>Loki</strong>, <strong>Tyr</strong>, and <strong>Norns</strong>. Every node represents a verifiable clause anchor.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => fetchMemoryMap()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E8E1D5] bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
            Refresh Topology
          </button>
        </div>
      </div>

      {/* Telemetry Strip */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
        <div className="bg-white border border-[#E8E1D5] rounded-xl p-3.5 shadow-xs">
          <span className="text-slate-500 font-semibold uppercase text-[10px] tracking-wider">Memory Nodes</span>
          <div className="text-xl font-bold font-mono text-[#17375B] mt-0.5">
            {data ? data.total_chunks : 0}
          </div>
          <span className="text-[10px] text-slate-400">Total clause chunks</span>
        </div>

        <div className="bg-white border border-[#E8E1D5] rounded-xl p-3.5 shadow-xs">
          <span className="text-slate-500 font-semibold uppercase text-[10px] tracking-wider">Thor Claims Plotted</span>
          <div className="text-xl font-bold font-mono text-amber-700 mt-0.5">
            {data ? data.total_facts : 0}
          </div>
          <span className="text-[10px] text-amber-700">Verified factual anchors</span>
        </div>

        <div className="bg-white border border-[#E8E1D5] rounded-xl p-3.5 shadow-xs">
          <span className="text-slate-500 font-semibold uppercase text-[10px] tracking-wider">Vector Matrix</span>
          <div className="text-xl font-bold text-emerald-700 mt-0.5">
            {data ? `${data.embedding_dim}-D Dense` : "128-D"}
          </div>
          <span className="text-[10px] text-emerald-600 font-mono">odin_vectors.npy</span>
        </div>

        <div className="bg-white border border-[#E8E1D5] rounded-xl p-3.5 shadow-xs">
          <span className="text-slate-500 font-semibold uppercase text-[10px] tracking-wider">Storage Engine</span>
          <div className="text-xl font-bold text-slate-800 mt-0.5">SQLite + NumPy</div>
          <span className="text-[10px] text-slate-400 font-mono">odin_chunks.db</span>
        </div>

        <div className="bg-white border border-[#E8E1D5] rounded-xl p-3.5 shadow-xs">
          <span className="text-slate-500 font-semibold uppercase text-[10px] tracking-wider">Consuming Agents</span>
          <div className="text-xl font-bold text-indigo-700 mt-0.5">5 Agents</div>
          <span className="text-[10px] text-indigo-600">Thor, Loki, Heimdall, Tyr, Norns</span>
        </div>
      </div>

      {/* Main Map & Filter Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left: Interactive Canvas (8 cols) */}
        <div className="xl:col-span-8 bg-white border border-[#E8E1D5] rounded-xl shadow-xs p-5 space-y-4 flex flex-col">
          {/* Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#E8E1D5]">
            {/* Search */}
            <div className="relative min-w-[200px] flex-1">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search claims, quotes, or chunk IDs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-[#E8E1D5] rounded-lg text-slate-900 focus:outline-hidden focus:border-[#17375B]"
              />
            </div>

            {/* Document Filter */}
            <select
              value={selectedDoc}
              onChange={(e) => setSelectedDoc(e.target.value)}
              className="text-xs bg-slate-50 border border-[#E8E1D5] rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-hidden"
            >
              <option value="all">All Documents</option>
              {docIds.map((doc) => (
                <option key={doc} value={doc}>
                  Doc: {doc}
                </option>
              ))}
            </select>

            {/* Claims only toggle */}
            <button
              onClick={() => setClaimsOnly(!claimsOnly)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                claimsOnly
                  ? "bg-amber-500 text-slate-900 shadow-xs"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {claimsOnly ? "Showing Claims Only" : "Show All Chunks"}
            </button>
          </div>

          {/* Dimension Pills */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-semibold text-slate-500 mr-1">Dimensions:</span>
            <button
              onClick={() => setSelectedDimension("all")}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                selectedDimension === "all"
                  ? "bg-[#17375B] text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              All ({data ? data.total_facts : 0})
            </button>
            {data?.dimensions.map((dim) => {
              const count = data.nodes.filter((n) => n.facts.some((f) => f.fact_type === dim)).length;
              const style = DIMENSION_COLORS[dim] || DIMENSION_COLORS.general;
              const active = selectedDimension === dim;
              return (
                <button
                  key={dim}
                  onClick={() => setSelectedDimension(dim)}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors flex items-center gap-1 ${
                    active ? "bg-[#17375B] text-white" : `${style.bg} ${style.text} border ${style.border}`
                  }`}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: style.fill }}
                  />
                  {dim} ({count})
                </button>
              );
            })}
          </div>

          {/* SVG Map Canvas */}
          <div className="relative w-full h-[520px] bg-[#0c1220] rounded-xl border border-slate-800 overflow-hidden select-none">
            {/* Grid background effect */}
            <svg
              className="absolute inset-0 w-full h-full opacity-15 pointer-events-none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#38bdf8" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>

            {loading ? (
              <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-xs gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-amber-500" />
                Projecting 128-dimensional vector space...
              </div>
            ) : (
              <svg
                viewBox="0 0 1000 660"
                className="w-full h-full cursor-crosshair"
              >
                {/* Render Edges (sequential document connections) */}
                <g className="opacity-25">
                  {data?.edges.map((edge, i) => {
                    const src = data.nodes.find((n) => n.id === edge.source);
                    const tgt = data.nodes.find((n) => n.id === edge.target);
                    if (!src || !tgt) return null;
                    return (
                      <line
                        key={`edge-${i}`}
                        x1={src.x}
                        y1={src.y}
                        x2={tgt.x}
                        y2={tgt.y}
                        stroke="#38bdf8"
                        strokeWidth="0.75"
                        strokeDasharray="2 3"
                      />
                    );
                  })}
                </g>

                {/* Render Non-claim background chunks */}
                {!claimsOnly && (
                  <g>
                    {filteredNodes
                      .filter((n) => !n.has_claims)
                      .map((node) => {
                        const isSelected = selectedNode?.id === node.id;
                        return (
                          <circle
                            key={node.id}
                            cx={node.x}
                            cy={node.y}
                            r={isSelected ? 5 : 2.5}
                            fill={isSelected ? "#f59e0b" : "#475569"}
                            className="cursor-pointer transition-all hover:scale-150"
                            onClick={() => setSelectedNode(node)}
                            onMouseEnter={() => setHoveredNode(node)}
                            onMouseLeave={() => setHoveredNode(null)}
                          />
                        );
                      })}
                  </g>
                )}

                {/* Render Claims (Beacon Nodes) */}
                <g>
                  {filteredNodes
                    .filter((n) => n.has_claims)
                    .map((node) => {
                      const isSelected = selectedNode?.id === node.id;
                      const isHovered = hoveredNode?.id === node.id;
                      const primaryFact = node.facts[0]?.fact_type || "general";
                      const color = DIMENSION_COLORS[primaryFact]?.fill || "#f59e0b";

                      return (
                        <g
                          key={node.id}
                          className="cursor-pointer group"
                          onClick={() => setSelectedNode(node)}
                          onMouseEnter={() => setHoveredNode(node)}
                          onMouseLeave={() => setHoveredNode(null)}
                        >
                          {/* Outer pulse aura */}
                          <circle
                            cx={node.x}
                            cy={node.y}
                            r={isSelected ? 14 : isHovered ? 11 : 7}
                            fill={color}
                            opacity={isSelected ? 0.35 : 0.18}
                            className="transition-all"
                          />
                          {/* Inner core node */}
                          <circle
                            cx={node.x}
                            cy={node.y}
                            r={isSelected ? 6 : 4}
                            fill={color}
                            stroke="#ffffff"
                            strokeWidth={isSelected ? 2 : 1}
                            className="transition-all"
                          />
                          {/* Label for selected / hovered */}
                          {(isSelected || isHovered) && (
                            <text
                              x={node.x}
                              y={node.y - 12}
                              textAnchor="middle"
                              fill="#ffffff"
                              fontSize="11"
                              fontWeight="bold"
                              fontFamily="monospace"
                              className="pointer-events-none drop-shadow-md"
                            >
                              {node.id}
                            </text>
                          )}
                        </g>
                      );
                    })}
                </g>
              </svg>
            )}

            {/* Bottom canvas legend */}
            <div className="absolute bottom-3 left-3 bg-slate-900/80 backdrop-blur-sm border border-slate-700 rounded-lg px-3 py-1.5 text-[10px] text-slate-300 flex items-center gap-3">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping inline-block" />
                Pulsing = Thor Verified Claim
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-slate-500 inline-block" />
                Dot = Indexed Clause Chunk
              </span>
              <span className="text-slate-400 font-mono">
                Showing {filteredNodes.length} / {data?.total_chunks || 0} nodes
              </span>
            </div>
          </div>
        </div>

        {/* Right: Node Detail & Agent Inspection Card (4 cols) */}
        <div className="xl:col-span-4 bg-white border border-[#E8E1D5] rounded-xl shadow-xs p-5 space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-[#E8E1D5] pb-3">
            <h3 className="font-bold text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Brain className="w-4 h-4 text-amber-600" />
              Shared Memory Inspector
            </h3>
            {selectedNode && (
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 font-bold">
                {selectedNode.id}
              </span>
            )}
          </div>

          {!selectedNode ? (
            <div className="py-24 text-center text-slate-400 text-xs">
              Click any node on the vector map to inspect its verified Thor claims and council actions.
            </div>
          ) : (
            <div className="space-y-4 text-xs">
              {/* Document metadata */}
              <div className="p-3 bg-slate-50 border border-[#E8E1D5] rounded-lg space-y-1.5 font-mono text-[11px]">
                <div className="flex items-center justify-between text-slate-700">
                  <span className="font-bold text-[#17375B]">{selectedNode.clause_ref || "Clause Ref"}</span>
                  <span className="text-slate-500">Page {selectedNode.page_num}</span>
                </div>
                <div className="text-slate-500 text-[10px]">
                  Document: {selectedNode.document_id}
                </div>
                <div className="text-slate-400 text-[10px]">
                  Coordinates: ({selectedNode.x}, {selectedNode.y}) &middot; Tokens: {selectedNode.token_count}
                </div>
              </div>

              {/* Verified Claims in this chunk */}
              <div className="space-y-2">
                <span className="font-bold text-slate-700 text-xs flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Thor Claims Grounded Here ({selectedNode.facts.length}):
                </span>

                {selectedNode.facts.length === 0 ? (
                  <div className="p-3 bg-slate-50 rounded-lg text-slate-500 text-[11px] italic">
                    This is an indexed clause chunk. No contractual risks or obligations were extracted from this specific text.
                  </div>
                ) : (
                  selectedNode.facts.map((fact, idx) => {
                    const style = DIMENSION_COLORS[fact.fact_type] || DIMENSION_COLORS.general;
                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border ${style.bg} ${style.border} space-y-1.5`}
                      >
                        <div className="flex items-center justify-between">
                          <span className={`font-bold font-mono text-[10px] uppercase ${style.text}`}>
                            {fact.fact_type}
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-slate-200 text-emerald-700 font-bold">
                            {fact.status} ({(fact.confidence * 100).toFixed(0)}%)
                          </span>
                        </div>

                        <div className="font-semibold text-slate-900 text-xs">
                          {fact.value}
                        </div>

                        <div className="border-l-2 border-amber-500 pl-2 text-[11px] text-slate-600 italic bg-white/70 p-1.5 rounded">
                          &ldquo;{fact.quote}&rdquo;
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Raw chunk snippet */}
              <div className="space-y-1">
                <span className="font-semibold text-slate-600 text-[11px]">Source Clause Snippet:</span>
                <div className="p-2.5 bg-slate-900 text-slate-200 font-mono text-[10px] rounded-lg max-h-36 overflow-y-auto leading-relaxed">
                  {selectedNode.text_snippet}
                </div>
              </div>

              {/* Consuming Council Agents */}
              <div className="pt-2 border-t border-[#E8E1D5] space-y-2">
                <span className="font-bold text-slate-700 text-[11px] uppercase tracking-wider block">
                  AI Council Consumers for this Memory:
                </span>
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div className="p-2 bg-cyan-50 border border-cyan-200 rounded text-cyan-900">
                    <span className="font-bold block flex items-center gap-1">
                      <Zap className="w-3 h-3" /> Thor
                    </span>
                    Verbatim extractor &amp; chunk anchor
                  </div>

                  <div className="p-2 bg-purple-50 border border-purple-200 rounded text-purple-900">
                    <span className="font-bold block flex items-center gap-1">
                      <Swords className="w-3 h-3" /> Loki
                    </span>
                    Challenges exposure &amp; breach risks
                  </div>

                  <div className="p-2 bg-emerald-50 border border-emerald-200 rounded text-emerald-900">
                    <span className="font-bold block flex items-center gap-1">
                      <Shield className="w-3 h-3" /> Heimdall
                    </span>
                    Validates against event logs
                  </div>

                  <div className="p-2 bg-rose-50 border border-rose-200 rounded text-rose-900">
                    <span className="font-bold block flex items-center gap-1">
                      <UserCheck className="w-3 h-3" /> Tyr
                    </span>
                    Rules &amp; drafts notice actions
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
