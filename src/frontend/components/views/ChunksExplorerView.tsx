"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Layers,
  Search,
  RefreshCw,
  Copy,
  Check,
  Eye,
  ExternalLink,
  Sparkles,
  FileText,
  Filter,
} from "lucide-react";

export interface ChunkFact {
  fact_type: string;
  value: string;
  confidence: number;
  status: string;
  quote: string;
}

export interface ChunkItem {
  chunk_id: string;
  document_id: string;
  clause_ref: string | null;
  text: string;
  page_num: number;
  token_count: number;
  rects?: number[][];
  source_type?: string;
  facts?: ChunkFact[];
}

interface ChunksExplorerViewProps {
  initialDocFilter?: string;
}

export function ChunksExplorerView({ initialDocFilter }: ChunksExplorerViewProps) {
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedDocFilter, setSelectedDocFilter] = useState<string>(initialDocFilter || "all");
  const [claimsOnlyFilter, setClaimsOnlyFilter] = useState<boolean>(false);
  const [selectedChunk, setSelectedChunk] = useState<ChunkItem | null>(null);
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);
  const [showPdfProof, setShowPdfProof] = useState<boolean>(false);

  const fetchChunks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = typeof window !== "undefined" ? localStorage.getItem("odin_token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      let loadedChunks: ChunkItem[] = [];
      const res = await fetch("/api/v1/workspace/chunks", { headers });
      if (res.ok) {
        const data = await res.json();
        loadedChunks = data.chunks || [];
      } else {
        const fallback = await fetch("/thor/api/chunks");
        if (fallback.ok) {
          const data = await fallback.json();
          loadedChunks = data.chunks || [];
        }
      }

      setChunks(loadedChunks);
      if (loadedChunks.length > 0) {
        setSelectedChunk((prev) => prev || loadedChunks[0]);
      }
    } catch (err: any) {
      setError(err?.message || "Could not connect to chunks API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchChunks();
  }, [fetchChunks]);

  const copyChunkText = (chunk: ChunkItem) => {
    navigator.clipboard.writeText(chunk.text);
    setCopiedChunkId(chunk.chunk_id);
    setTimeout(() => setCopiedChunkId(null), 2000);
  };

  const chunkDocIds = useMemo(() => {
    const set = new Set<string>();
    chunks.forEach((c) => set.add(c.document_id));
    return Array.from(set).sort();
  }, [chunks]);

  const filteredChunks = useMemo(() => {
    return chunks.filter((c) => {
      const matchesDoc = selectedDocFilter === "all" || c.document_id === selectedDocFilter;
      const matchesClaims = !claimsOnlyFilter || (c.facts && c.facts.length > 0);
      const q = searchQuery.toLowerCase();
      const matchesQuery =
        !q ||
        c.chunk_id.toLowerCase().includes(q) ||
        (c.clause_ref && c.clause_ref.toLowerCase().includes(q)) ||
        c.text.toLowerCase().includes(q) ||
        c.document_id.toLowerCase().includes(q);
      return matchesDoc && matchesClaims && matchesQuery;
    });
  }, [chunks, selectedDocFilter, claimsOnlyFilter, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Top Filter & Metrics Bar */}
      <div className="bg-white border border-[#E8E1D5] rounded-xl p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-1 items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search chunk ID (e.g. B1:5.2, STD:6.3) or verbatim clause text..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[#E8E1D5] focus:outline-none focus:border-[#17375B] bg-slate-50/50"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedDocFilter}
              onChange={(e) => setSelectedDocFilter(e.target.value)}
              className="text-xs py-2 px-3 border border-[#E8E1D5] rounded-lg bg-slate-50 text-slate-700 font-medium focus:outline-none focus:border-[#17375B]"
            >
              <option value="all">All Documents ({chunks.length})</option>
              {chunkDocIds.map((doc) => (
                <option key={doc} value={doc}>
                  {doc}
                </option>
              ))}
            </select>
          </div>

          <label className="flex items-center gap-1.5 text-xs text-slate-700 font-medium cursor-pointer select-none">
            <input
              type="checkbox"
              checked={claimsOnlyFilter}
              onChange={(e) => setClaimsOnlyFilter(e.target.checked)}
              className="rounded text-[#17375B] focus:ring-0"
            />
            <span>With Thor Facts Only</span>
          </label>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchChunks}
            className="flex items-center gap-1 px-2.5 py-1.5 border border-[#E8E1D5] rounded-lg text-xs hover:bg-slate-50 text-slate-600 transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <div className="text-xs text-slate-500 font-mono flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>
              Showing <strong>{filteredChunks.length}</strong> of {chunks.length} Chunks
            </span>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg">
          {error}
        </div>
      )}

      {/* 2-Column Chunks Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Chunks List */}
        <div className="lg:col-span-5 bg-white border border-[#E8E1D5] rounded-xl shadow-xs p-4 space-y-2 max-h-[750px] overflow-y-auto">
          {loading ? (
            <div className="py-20 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-[#17375B]" />
              Loading ChromaDB chunks...
            </div>
          ) : filteredChunks.length === 0 ? (
            <div className="py-20 text-center text-xs text-slate-500">
              No chunks match the current search or document filter.
            </div>
          ) : (
            filteredChunks.map((chunk) => {
              const isSelected = selectedChunk?.chunk_id === chunk.chunk_id;
              const hasFacts = chunk.facts && chunk.facts.length > 0;
              return (
                <div
                  key={chunk.chunk_id}
                  onClick={() => {
                    setSelectedChunk(chunk);
                    setShowPdfProof(false);
                  }}
                  className={`p-3 rounded-lg border transition-all cursor-pointer ${
                    isSelected
                      ? "border-[#17375B] bg-blue-50/50 shadow-xs"
                      : "border-[#E8E1D5] hover:border-slate-300 bg-white"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[#17375B] bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                        {chunk.chunk_id}
                      </span>
                      {chunk.page_num && (
                        <span className="text-[10px] font-mono text-slate-500">
                          p.{chunk.page_num}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      {hasFacts && (
                        <span className="px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded text-[10px] font-bold">
                          {chunk.facts!.length} facts
                        </span>
                      )}
                      <span className="text-[10px] font-mono text-slate-400">
                        {chunk.token_count} tok
                      </span>
                    </div>
                  </div>

                  {chunk.clause_ref && (
                    <div className="text-xs font-semibold text-slate-800 mt-1 line-clamp-1">
                      {chunk.clause_ref}
                    </div>
                  )}

                  <div className="text-[11px] text-slate-600 line-clamp-2 mt-1 font-sans">
                    {chunk.text}
                  </div>

                  <div className="text-[10px] font-mono text-slate-400 mt-1 flex items-center justify-between">
                    <span>{chunk.document_id}</span>
                    {chunk.rects && chunk.rects.length > 0 && (
                      <span className="text-emerald-700 font-semibold">&bull; PDF Rects Mapped</span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Chunk Deep-Dive Inspector */}
        <div className="lg:col-span-7 bg-white border border-[#E8E1D5] rounded-xl shadow-xs p-5">
          {!selectedChunk ? (
            <div className="py-24 text-center text-xs text-slate-500 flex flex-col items-center justify-center gap-2">
              <Layers className="w-8 h-8 text-slate-300" />
              Select a chunk on the left to inspect verbatim text, PyMuPDF twin bounding boxes, and extracted facts.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Header */}
              <div className="flex items-start justify-between gap-4 border-b border-[#E8E1D5] pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-base font-bold text-[#17375B]">
                      {selectedChunk.chunk_id}
                    </span>
                    {selectedChunk.page_num && (
                      <span className="text-xs font-mono bg-blue-100 text-blue-900 px-2 py-0.5 rounded font-semibold">
                        Page {selectedChunk.page_num}
                      </span>
                    )}
                    <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      {selectedChunk.token_count} tokens
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 font-mono mt-1">
                    Source Document: <strong className="text-slate-800">{selectedChunk.document_id}</strong>
                  </div>
                  {selectedChunk.clause_ref && (
                    <div className="text-sm font-semibold text-slate-900 mt-1">
                      {selectedChunk.clause_ref}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copyChunkText(selectedChunk)}
                    className="px-2.5 py-1.5 rounded-lg border border-[#E8E1D5] bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-medium flex items-center gap-1.5 transition-colors"
                  >
                    {copiedChunkId === selectedChunk.chunk_id ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-700">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-slate-500" />
                        <span>Copy Text</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setShowPdfProof(!showPdfProof)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                      showPdfProof
                        ? "bg-[#17375B] text-white"
                        : "border border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100"
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    {showPdfProof ? "Hide PDF Proof" : "View PDF Page Highlight"}
                  </button>
                </div>
              </div>

              {/* Inline PDF Highlight Proof viewer */}
              {showPdfProof && (
                <div className="p-3 bg-slate-900 rounded-lg text-slate-200 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-mono">
                      PyMuPDF High-Res Highlight Proof &middot; Page {selectedChunk.page_num}
                    </span>
                    <a
                      href={`/thor/api/pdf_page?doc=${encodeURIComponent(
                        selectedChunk.document_id.replace(/^contracts\//, "").replace(/\.txt$/, "")
                      )}&page=${selectedChunk.page_num}&chunk_id=${encodeURIComponent(
                        selectedChunk.chunk_id
                      )}&format=png`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-amber-400 hover:underline flex items-center gap-1 text-[11px]"
                    >
                      <ExternalLink className="w-3 h-3" /> Full Size PNG
                    </a>
                  </div>
                  <div className="bg-black rounded border border-slate-800 p-2 flex justify-center max-h-[380px] overflow-auto">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`/thor/api/pdf_page?doc=${encodeURIComponent(
                        selectedChunk.document_id.replace(/^contracts\//, "").replace(/\.txt$/, "")
                      )}&page=${selectedChunk.page_num}&chunk_id=${encodeURIComponent(
                        selectedChunk.chunk_id
                      )}&format=png`}
                      alt={`Proof highlight for ${selectedChunk.chunk_id}`}
                      className="max-w-full rounded shadow-md object-contain"
                    />
                  </div>
                </div>
              )}

              {/* Verbatim Chunk Text */}
              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Verbatim Chunk Text (ChromaDB Vector Payload):
                </span>
                <div className="p-3 bg-slate-900 text-slate-100 font-mono text-xs rounded-lg max-h-64 overflow-y-auto whitespace-pre-wrap leading-relaxed border border-slate-800">
                  {selectedChunk.text}
                </div>
              </div>

              {/* Extracted Facts Table */}
              {selectedChunk.facts && selectedChunk.facts.length > 0 && (
                <div className="space-y-2 pt-2">
                  <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                    Facts Extracted by Thor Sub-Agent ({selectedChunk.facts.length}):
                  </span>

                  <div className="border border-[#E8E1D5] rounded-lg overflow-hidden divide-y divide-[#E8E1D5]">
                    {selectedChunk.facts.map((fact, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-slate-50/70 hover:bg-white transition-colors text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-slate-800 uppercase text-[11px] bg-slate-200/80 px-1.5 py-0.5 rounded">
                            {fact.fact_type}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono font-semibold text-emerald-700">
                              {Math.round(fact.confidence * 100)}% Conf
                            </span>
                            <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] rounded font-bold uppercase">
                              {fact.status}
                            </span>
                          </div>
                        </div>

                        <div className="text-slate-900 font-medium">{fact.value}</div>

                        {fact.quote && (
                          <div className="text-[11px] text-slate-500 italic border-l-2 border-amber-400 pl-2 mt-1">
                            &ldquo;{fact.quote}&rdquo;
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* PyMuPDF Bounding Rects */}
              {selectedChunk.rects && selectedChunk.rects.length > 0 && (
                <div className="space-y-1 pt-1">
                  <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                    PyMuPDF Twin Bounding Box Coordinates:
                  </span>
                  <div className="p-2 bg-slate-50 border border-[#E8E1D5] rounded text-[11px] font-mono text-slate-600 flex flex-wrap gap-2">
                    {selectedChunk.rects.map((r, i) => (
                      <span key={i} className="bg-white px-2 py-0.5 rounded border border-slate-200">
                        Rect {i + 1}: [{r.map((v) => Number(v.toFixed(1))).join(", ")}]
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
