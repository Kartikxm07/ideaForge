"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  ArrowUpRight,
  FileText,
  MessageSquare,
  GitBranch,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  Calendar,
  AlertCircle,
  Activity,
  CheckCircle2,
  RefreshCw,
  Clock,
  Layers,
  Search,
  ExternalLink,
  ChevronDown
} from "lucide-react";
import type { OdinRun, OdinContract } from "@/lib/odin-api";

// Built-in dataset records from odin_dev_pack/bundle/data
const PACK_LEDGER_ITEMS = [
  { id: "leg-01", date: "2026-09-01", type: "ledger", title: "StratoNode Cloud Hosting Fee", amount: "$12,500.00", ref: "INV-2026-0901", status: "cleared", from: "Quillhub Inc.", to: "StratoNode Inc.", detail: "Monthly hosting infrastructure payable for primary Kubernetes cluster." },
  { id: "leg-02", date: "2026-10-01", type: "ledger", title: "StratoNode Cloud Hosting Fee", amount: "$12,500.00", ref: "INV-2026-1001", status: "cleared", from: "Quillhub Inc.", to: "StratoNode Inc.", detail: "Monthly hosting infrastructure payable. Incident credit requested." },
  { id: "leg-03", date: "2026-10-15", type: "ledger", title: "Harbor Retail Q3 Enterprise Subscription", amount: "+$45,000.00", ref: "REC-2026-1015", status: "cleared", from: "Harbor Retail Solutions LLC", to: "Quillhub Inc.", detail: "Enterprise quarterly route optimization platform subscription receivable." },
  { id: "leg-04", date: "2026-11-01", type: "ledger", title: "StratoNode Cloud Hosting Fee", amount: "$12,500.00", ref: "INV-2026-1101", status: "cleared", from: "Quillhub Inc.", to: "StratoNode Inc.", detail: "Monthly hosting infrastructure payable." },
  { id: "leg-05", date: "2026-11-15", type: "ledger", title: "Vantage Logistics Platform Licensing", amount: "+$30,000.00", ref: "REC-2026-1115", status: "pending", from: "Vantage Logistics Corp.", to: "Quillhub Inc.", detail: "Annual route optimization licensing fee receivable (pending invoice dispute reconciliation)." },
  { id: "leg-06", date: "2026-11-20", type: "ledger", title: "Pixelwright Design Studio Milestone 1", amount: "$8,500.00", ref: "INV-PIX-101", status: "cleared", from: "Quillhub Inc.", to: "Pixelwright Design Studio LLC", detail: "Independent UI/UX contractor milestone 1 delivery acceptance payment." },
];

const PACK_HOLIDAYS = [
  { id: "hol-01", date: "2026-05-25", type: "holiday", title: "Memorial Day", observed_by: "US", detail: "Banking and contractual notice holiday. SLA business day countdowns paused." },
  { id: "hol-02", date: "2026-07-04", type: "holiday", title: "Independence Day", observed_by: "US", detail: "Observed business holiday. Core operational SLA windows paused." },
  { id: "hol-03", date: "2026-09-07", type: "holiday", title: "Labor Day", observed_by: "US", detail: "Observed business holiday across US corporate facilities." },
  { id: "hol-04", date: "2026-11-26", type: "holiday", title: "Thanksgiving Day", observed_by: "US", detail: "Notice & cure period suspension date per Standard Terms §14.2." },
  { id: "hol-05", date: "2026-12-25", type: "holiday", title: "Christmas Day", observed_by: "US/UK", detail: "Dual jurisdiction holiday. Financial settlements & bank transfers freeze." },
  { id: "hol-06", date: "2027-01-01", type: "holiday", title: "New Year's Day", observed_by: "US/UK", detail: "Contract renewal notification window boundary." },
  { id: "hol-07", date: "2027-05-25", type: "holiday", title: "Memorial Day", observed_by: "US", detail: "Contractual business holiday." },
  { id: "hol-08", date: "2027-07-04", type: "holiday", title: "Independence Day", observed_by: "US", detail: "Contractual business holiday." },
];

export interface LiveStreamItem {
  id: string;
  date: string;
  type: "event" | "ledger" | "holiday" | "ruling" | "milestone";
  title: string;
  category: string;
  badge: string;
  badgeColor: string;
  detail: string;
  source?: string;
  meta?: Record<string, any>;
}

export function LiveTimelineScroller({ run }: { run: OdinRun }) {
  const [items, setItems] = useState<LiveStreamItem[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [selectedItem, setSelectedItem] = useState<LiveStreamItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [scrollProgress, setScrollProgress] = useState<number>(0);
  const [activeDateRange, setActiveDateRange] = useState<string>("Loading stream...");
  const [showGuide, setShowGuide] = useState<boolean>(true);
  const [rippleCard, setRippleCard] = useState<string | null>(null);
  const [popupItem, setPopupItem] = useState<LiveStreamItem | null>(null);
  const [popupVisible, setPopupVisible] = useState<boolean>(false);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const guideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-dismiss guide after 5s
  useEffect(() => {
    guideTimerRef.current = setTimeout(() => setShowGuide(false), 5000);
    return () => { if (guideTimerRef.current) clearTimeout(guideTimerRef.current); };
  }, []);

  const handleCardClick = useCallback((item: LiveStreamItem) => {
    // Ripple animation on clicked card
    setRippleCard(item.id);
    setTimeout(() => setRippleCard(null), 600);
    // Open animated detail popup
    setPopupItem(item);
    setPopupVisible(false);
    requestAnimationFrame(() => requestAnimationFrame(() => setPopupVisible(true)));
    setSelectedItem(item);
    setShowGuide(false);
    if (guideTimerRef.current) clearTimeout(guideTimerRef.current);
  }, []);

  const closePopup = useCallback(() => {
    setPopupVisible(false);
    setTimeout(() => { setPopupItem(null); setSelectedItem(null); }, 300);
  }, []);

  // Fetch operational events and synthesize full live timeline stream
  const fetchLiveStream = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/workspace/events", { credentials: "same-origin" });
      let opEvents: any[] = [];
      if (res.ok) {
        opEvents = await res.json();
      }

      // Convert operational events
      const convertedEvents: LiveStreamItem[] = (opEvents || []).map((e: any) => ({
        id: e.id || e.event_id,
        date: (e.occurred_at || e.timestamp || "").slice(0, 10),
        type: "event" as const,
        title: e.subject || `Operational Event ${e.event_id}`,
        category: e.channel || "Incident & Comms",
        badge: e.event_id || "EVENT",
        badgeColor: e.subject?.toLowerCase().includes("outage") || e.subject?.toLowerCase().includes("disruption")
          ? "bg-rose-100 text-rose-800 border-rose-300"
          : "bg-indigo-100 text-indigo-800 border-indigo-300",
        detail: e.body || "No details provided",
        source: `Channel: ${e.channel} | From: ${e.sender || e.from} → ${e.recipient || e.to}`,
        meta: e
      }));

      // Convert ledger items
      const convertedLedger: LiveStreamItem[] = PACK_LEDGER_ITEMS.map((l) => ({
        id: l.id,
        date: l.date,
        type: "ledger" as const,
        title: `${l.title} (${l.amount})`,
        category: "AP/AR Ledger",
        badge: l.status.toUpperCase(),
        badgeColor: l.amount.startsWith("+")
          ? "bg-emerald-100 text-emerald-800 border-emerald-300"
          : "bg-blue-100 text-blue-800 border-blue-300",
        detail: l.detail,
        source: `${l.from} → ${l.to} · Ref: ${l.ref}`,
        meta: l
      }));

      // Convert holidays
      const convertedHolidays: LiveStreamItem[] = PACK_HOLIDAYS.map((h) => ({
        id: h.id,
        date: h.date,
        type: "holiday" as const,
        title: `Holiday: ${h.title} (${h.observed_by})`,
        category: "Business Calendar",
        badge: "HOLIDAY",
        badgeColor: "bg-amber-100 text-amber-800 border-amber-300",
        detail: h.detail,
        source: `Observed by: ${h.observed_by}`,
        meta: h
      }));

      // Convert Tyr rulings from the active run
      const convertedRulings: LiveStreamItem[] = (run.rulings || []).map((r: any, idx: number) => ({
        id: r.id || `ruling-${idx}`,
        date: r.clock_t || r.created_at?.slice(0, 10) || "2027-03-15",
        type: "ruling" as const,
        title: `Tyr Ruling: ${r.outcome ? r.outcome.toUpperCase() : "HEARING"}`,
        category: "Council Rulings",
        badge: r.outcome?.toUpperCase() || "RULING",
        badgeColor: r.outcome === "upheld"
          ? "bg-red-100 text-red-800 border-red-300"
          : r.outcome === "rejected"
          ? "bg-slate-100 text-slate-800 border-slate-300"
          : "bg-yellow-100 text-yellow-800 border-yellow-300",
        detail: r.rationale || "Adjudicated against verified contract extractions.",
        source: r.citations?.length ? `${r.citations[0].document_key} · ${r.citations[0].clause_ref}` : "Council Deliberation",
        meta: r
      }));

      // Merge and sort all items chronologically
      const allMerged = [...convertedEvents, ...convertedLedger, ...convertedHolidays, ...convertedRulings]
        .filter((item) => Number.isFinite(Date.parse(item.date)))
        .sort((a, b) => a.date.localeCompare(b.date));

      setItems(allMerged);
      if (allMerged.length > 0) {
        setActiveDateRange(`${allMerged[0].date} → ${allMerged[allMerged.length - 1].date}`);
      }
    } catch (err) {
      console.error("Failed to fetch live stream:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveStream();
  }, [run.id]);

  const handleScroll = () => {
    if (!scrollerRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = scrollerRef.current;
    const maxScroll = scrollWidth - clientWidth;
    const progress = maxScroll > 0 ? (scrollLeft / maxScroll) * 100 : 0;
    setScrollProgress(Math.round(progress));

    // Calculate approximate date window based on scroll
    const filtered = filteredItems();
    if (filtered.length > 0) {
      const idx = Math.min(
        filtered.length - 1,
        Math.floor((scrollLeft / (maxScroll || 1)) * (filtered.length - 1))
      );
      const curr = filtered[idx];
      if (curr) {
        setActiveDateRange(`Viewing: ${curr.date} (${curr.category})`);
      }
    }
  };

  const scrollHorizontally = (direction: "left" | "right") => {
    if (!scrollerRef.current) return;
    const offset = direction === "left" ? -420 : 420;
    scrollerRef.current.scrollBy({ left: offset, behavior: "smooth" });
  };

  const filteredItems = () => {
    if (filter === "all") return items;
    if (filter === "event") return items.filter((i) => i.type === "event");
    if (filter === "ledger") return items.filter((i) => i.type === "ledger");
    if (filter === "holiday") return items.filter((i) => i.type === "holiday");
    if (filter === "ruling") return items.filter((i) => i.type === "ruling");
    return items;
  };

  const visibleList = filteredItems();

  return (
    <div className="mt-6 rounded-2xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-6 shadow-sm">
      {/* Header Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <p className="text-xs font-bold tracking-wider uppercase text-emerald-800">
              Live Horizontal Operational & Financial Stream
            </p>
          </div>
          <h3 className="mt-1 text-lg font-bold text-slate-900">
            Chronological Events, Ledger AP/AR & Council Updates
          </h3>
          <p className="text-xs text-slate-500">
            Scroll horizontally to navigate from 2026 contract inception through 2027 checkpoints.
          </p>
        </div>

        {/* Live Controls */}
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700">
            {activeDateRange}
          </div>
          <button
            onClick={fetchLiveStream}
            disabled={loading}
            title="Refresh stream"
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
          >
            <RefreshCw size={13} className={loading ? "animate-spin text-emerald-600" : ""} />
            Sync
          </button>
          <div className="flex items-center gap-1 border-l border-slate-200 pl-2">
            <button
              onClick={() => scrollHorizontally("left")}
              className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 hover:bg-slate-50 transition"
              aria-label="Scroll left"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => scrollHorizontally("right")}
              className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 hover:bg-slate-50 transition"
              aria-label="Scroll right"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Filter Chips Bar */}
      <div className="mt-4 flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3">
        {[
          { key: "all", label: `All Updates (${items.length})` },
          { key: "event", label: `⚡ Incidents & Comms (${items.filter((i) => i.type === "event").length})` },
          { key: "ledger", label: `💳 AP/AR Ledger (${items.filter((i) => i.type === "ledger").length})` },
          { key: "ruling", label: `⚖️ Council Rulings (${items.filter((i) => i.type === "ruling").length})` },
          { key: "holiday", label: `📅 Calendar Holidays (${items.filter((i) => i.type === "holiday").length})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              filter === tab.key
                ? "bg-[#26715b] text-white shadow-sm"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Horizontal Scroll Progress Bar */}
      <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full bg-gradient-to-r from-[#26715b] to-emerald-400 transition-all duration-150"
          style={{ width: `${Math.max(5, scrollProgress)}%` }}
        />
      </div>

      {/* Horizontal Scroller Container */}
      <div
        ref={scrollerRef}
        onScroll={handleScroll}
        className="mt-4 flex gap-4 overflow-x-auto pb-4 pt-1 scroll-smooth"
        style={{ scrollbarWidth: "thin" }}
      >
        {/* Guide Tooltip — appears on first load, dismisses on click */}
        {showGuide && visibleList.length > 0 && (
          <div className="absolute z-30 flex items-center gap-2 bg-[#26715b] text-white text-xs font-semibold rounded-xl px-3 py-2 shadow-lg pointer-events-none"
            style={{ top: "auto", marginTop: "6px", marginLeft: "8px" }}
          >
            <span className="animate-bounce">👆</span>
            Click any card for full details
            <svg width="18" height="10" className="inline ml-1 animate-pulse" viewBox="0 0 18 10">
              <path d="M0 5 L12 5 M10 2 L14 5 L10 8" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
            </svg>
          </div>
        )}

        {visibleList.length ? (
          visibleList.map((item, cardIdx) => (
            <div
              key={item.id}
              onClick={() => handleCardClick(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleCardClick(item); }
              }}
              className={`group relative flex w-[320px] shrink-0 cursor-pointer flex-col justify-between rounded-xl border p-4 transition-all duration-200 hover:-translate-y-1.5 hover:shadow-lg overflow-hidden ${
                selectedItem?.id === item.id
                  ? "border-[#26715b] bg-[#f0f7f4] ring-2 ring-[#26715b]/30 shadow-md"
                  : "border-slate-200 bg-white hover:border-[#26715b]/60"
              }`}
            >
              {/* Ripple animation overlay */}
              {rippleCard === item.id && (
                <span className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <span className="block h-full w-full rounded-xl bg-[#26715b]/10 animate-ping" style={{ animationDuration: "0.5s", animationIterationCount: "1" }} />
                </span>
              )}

              {/* Shimmer hover overlay */}
              <span className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                style={{ background: "linear-gradient(110deg, transparent 40%, rgba(38,113,91,0.06) 60%, transparent 70%)" }} />

              <div>
                {/* Card Top: Date & Category Badge */}
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                    <Clock size={12} className="text-[#26715b]" />
                    {item.date}
                  </span>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${item.badgeColor}`}
                  >
                    {item.badge}
                  </span>
                </div>

                {/* Card Title */}
                <h4 className="mt-2.5 text-sm font-semibold text-slate-900 line-clamp-2 group-hover:text-[#26715b] transition">
                  {item.title}
                </h4>

                {/* Card Body Preview */}
                <p className="mt-1.5 text-xs text-slate-600 line-clamp-3 leading-relaxed">
                  {item.detail}
                </p>
              </div>

              {/* Card Bottom Meta */}
              <div className="mt-3 border-t border-slate-100 pt-2 flex items-center justify-between text-[11px] text-slate-500">
                <span className="truncate max-w-[210px]">{item.source || item.category}</span>
                <span className="text-[#26715b] font-semibold group-hover:translate-x-0.5 transition flex items-center gap-1">
                  View full
                  <ChevronRight size={12} />
                </span>
              </div>

              {/* Guide arrow on first card */}
              {showGuide && cardIdx === 0 && (
                <div className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 flex flex-col items-center pointer-events-none">
                  <div className="h-1.5 w-1.5 rounded-full bg-[#26715b] animate-bounce" />
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="w-full py-8 text-center text-xs text-slate-500">
            No updates found matching this filter.
          </div>
        )}
      </div>

      {/* Animated Slide-Up Detail Modal */}
      {popupItem && (
        <div
          className={`mt-4 rounded-2xl border bg-gradient-to-br from-white to-[#f0f7f4] shadow-xl transition-all duration-300 overflow-hidden ${
            popupVisible
              ? "opacity-100 translate-y-0 max-h-[600px]"
              : "opacity-0 translate-y-4 max-h-0"
          }`}
          style={{ borderColor: "#26715b55" }}
        >
          <div className="p-5">
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-3 pb-4 border-b border-[#26715b]/15">
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider ${popupItem.badgeColor}`}>
                    {popupItem.category}
                  </span>
                  <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider ${popupItem.badgeColor}`}>
                    {popupItem.badge}
                  </span>
                  <span className="flex items-center gap-1 text-xs font-semibold text-slate-600">
                    <Clock size={11} className="text-[#26715b]" />
                    {popupItem.date}
                  </span>
                </div>
                <h4 className="mt-2 text-base font-bold text-slate-900 leading-snug">{popupItem.title}</h4>
              </div>
              <button
                onClick={closePopup}
                className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition flex items-center gap-1 shrink-0"
              >
                <ChevronDown size={13} />
                Close
              </button>
            </div>

            {/* Modal Body */}
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-[#26715b] mb-1.5">Full Details</p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{popupItem.detail}</p>
              </div>
              <div className="space-y-3">
                {popupItem.source && (
                  <div className="rounded-xl border border-slate-200 bg-white/80 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Source Anchor</p>
                    <p className="text-xs text-slate-700 leading-relaxed">{popupItem.source}</p>
                  </div>
                )}
                {popupItem.meta && Object.keys(popupItem.meta).length > 0 && (
                  <div className="rounded-xl border border-slate-200 bg-white/80 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">Metadata</p>
                    <div className="space-y-1">
                      {Object.entries(popupItem.meta).filter(([k]) => !["id","detail","meta"].includes(k)).slice(0, 5).map(([k, v]) => (
                        <div key={k} className="flex justify-between gap-2 text-[11px]">
                          <span className="text-slate-500 capitalize">{k.replace(/_/g," ")}</span>
                          <span className="text-slate-800 font-medium text-right truncate max-w-[100px]">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* Navigation hint */}
                <div className="rounded-xl border border-[#26715b]/20 bg-[#f0f7f4]/60 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[#26715b]/70 mb-1">Navigation</p>
                  <p className="text-[11px] text-slate-600">Scroll horizontally through the timeline above to explore more events. Click any card to view full details here.</p>
                  <div className="flex items-center gap-1 mt-2 text-[11px] text-[#26715b] font-medium">
                    <ChevronLeft size={12} />
                    Scroll left / right
                    <ChevronRight size={12} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function ObligationGraph({ run }: { run: OdinRun }) {
  const rows = [...run.timeline].filter(r => Number.isFinite(Date.parse(r.date))).sort((a,b) => a.date.localeCompare(b.date));
  const [selected, setSelected] = useState<string | null>(null);
  const chosen = rows.find(r => r.id === selected);
  const start = rows.length ? Date.parse(rows[0].date) : 0;
  const span = rows.length ? Math.max(86400000, Date.parse(rows[rows.length - 1].date) - start) : 1;
  return (
    <section className="workspace-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="workspace-eyebrow">THE BIG PICTURE</p>
          <h2 className="mt-1 text-xl font-semibold">Obligation timeline</h2>
        </div>
        <span className="workspace-tag">{rows.length} sourced milestones</span>
      </div>
      <p className="mt-2 text-sm text-slate-500">
        Explore contract dates. Select a milestone to see the evidence behind it.
      </p>

      {rows.length ? (
        <>
          <div className="mt-6 overflow-x-auto">
            <svg
              viewBox={`0 0 850 ${Math.max(180, rows.length * 44 + 65)}`}
              className="min-w-[650px] w-full"
              role="img"
              aria-label="Dated contract obligations, earliest to latest"
            >
              {[0, 0.25, 0.5, 0.75, 1].map((t) => (
                <g key={t}>
                  <line
                    x1={220 + t * 570}
                    x2={220 + t * 570}
                    y1={25}
                    y2={rows.length * 44 + 30}
                    stroke="#e2e8e5"
                    strokeDasharray="4 5"
                  />
                  <text
                    x={220 + t * 570}
                    y={15}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#64746b"
                  >
                    {new Date(start + t * span).toISOString().slice(0, 10)}
                  </text>
                </g>
              ))}
              {rows.map((r, i) => {
                const x = 220 + ((Date.parse(r.date) - start) / span) * 570;
                const y = 50 + i * 44;
                return (
                  <g key={r.id}>
                    <text x={0} y={y + 4} fill="#344c42" fontSize="11">
                      {r.document_key.slice(0, 26)}
                    </text>
                    <line x1={215} x2={800} y1={y} y2={y} stroke="#f0f3f1" />
                    <g
                      role="button"
                      tabIndex={0}
                      aria-label={`${r.date}: ${r.description}`}
                      className="cursor-pointer"
                      onClick={() => setSelected(r.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelected(r.id);
                        }
                      }}
                    >
                      <title>{r.description}</title>
                      <circle cx={x} cy={y} r={17} fill="transparent" />
                      <circle
                        cx={x}
                        cy={y}
                        r={selected === r.id ? 8 : 6}
                        fill={selected === r.id ? "#bf8c3e" : "#26715b"}
                      />
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>

          {chosen && (
            <div className="mt-3 rounded-xl bg-[#f0f5f1] p-4">
              <p className="text-xs font-semibold text-[#26715b]">
                {chosen.date} · {chosen.document_key} · {chosen.citation.clause_ref}
              </p>
              <p className="mt-2 text-sm font-medium">{chosen.description}</p>
              <blockquote className="mt-2 border-l-2 border-[#bf8c3e] pl-3 text-sm text-slate-600">
                {chosen.citation.quote}
              </blockquote>
              <a
                className="mt-3 inline-block text-xs font-semibold underline"
                target="_blank"
                rel="noreferrer"
                href={`/api/v1/workspace/contracts/${encodeURIComponent(chosen.document_key)}/source`}
              >
                Open source document
              </a>
            </div>
          )}
        </>
      ) : (
        <div className="my-8 rounded-xl border border-dashed border-[#d4ddd5] p-8 text-center">
          <GitBranch className="mx-auto mb-3 text-[#879b8e]" />
          <p className="font-medium">Your contract timeline starts here</p>
          <p className="mt-2 text-sm text-slate-500">
            Upload contracts and run the agents to extract dated obligations.
          </p>
        </div>
      )}

      {/* Live Horizontal Scroller Below the Obligation Graph */}
      <LiveTimelineScroller run={run} />
    </section>
  );
}

export function WorkspaceOverview({
  run,
  contracts,
  navigate,
}: {
  run: OdinRun;
  contracts: OdinContract[];
  navigate: (view: "odin_web" | "trial" | "time" | "ask" | "debate") => void;
}) {
  return (
    <div className="space-y-6">
      <section className="workspace-hero">
        <div className="max-w-xl">
          <p className="text-xs font-semibold tracking-[.18em] text-[#bfcebd]">
            FROM DOCUMENTS TO DECISIONS
          </p>
          <h2 className="mt-5 text-3xl font-medium leading-tight sm:text-4xl">
            Every clause.<br />
            A clearer picture.
          </h2>
          <p className="mt-4 max-w-md text-sm leading-6 text-[#d0dbcf]">
            Bring your contracts, evidence, and agent reasoning together. Know what matters, when it matters, and why.
          </p>
          <button
            className="mt-6 inline-flex items-center gap-3 rounded-lg bg-[#e4efcc] px-5 py-3 text-sm font-semibold text-[#203c30]"
            onClick={() => navigate("ask")}
          >
            Ask your documents <ArrowUpRight size={17} />
          </button>
        </div>
        <div className="hidden w-52 shrink-0 space-y-3 lg:block">
          {["01 / Collect evidence", "02 / Challenge assumptions", "03 / Reach a decision"].map(
            (s, i) => (
              <div
                key={s}
                className="rounded-xl border border-white/15 bg-white/5 p-4 text-sm text-[#e1e9dd]"
                style={{ marginLeft: i * 12 }}
              >
                {s}
              </div>
            )
          )}
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        {[
          {
            icon: FileText,
            title: "Document library",
            detail: `${contracts.length} contracts in your workspace. Inspect source text, chunks, and memory.`,
            view: "odin_web" as const,
          },
          {
            icon: GitBranch,
            title: "Agent deliberation",
            detail: "Follow evidence gathering, claims, challenges, and the final briefing.",
            view: "trial" as const,
          },
          {
            icon: MessageSquare,
            title: "Evidence-backed Q&A",
            detail: "Ask a focused question and revisit answers with their original citations.",
            view: "ask" as const,
          },
        ].map((c) => (
          <button
            key={c.title}
            onClick={() => navigate(c.view)}
            className="workspace-panel text-left hover:border-[#93aa98]"
          >
            <c.icon size={21} className="text-[#39745b]" />
            <h3 className="mt-4 font-semibold">{c.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-500">{c.detail}</p>
            <ArrowRight size={17} className="mt-4 text-[#39745b]" />
          </button>
        ))}
      </div>

      {/* Obligation Timeline and live horizontal scroller below it */}
      <ObligationGraph run={run} />

      <section className="workspace-panel">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">How the council reaches a decision</h2>
          <button
            className="text-xs font-semibold text-[#26715b]"
            onClick={() => navigate("debate")}
          >
            Open debate →
          </button>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["Thor", "Extract cited contract terms"],
            ["Heimdall", "Check operational evidence"],
            ["Loki", "Challenge claims and assumptions"],
            ["Tyr", "Adjudicate supported findings"],
            ["Norns", "Project conditional scenarios"],
          ].map(([name, detail], i) => (
            <div key={name} className="border-t border-[#d9e2d9] pt-4">
              <span className="text-xs text-[#7d937f]">0{i + 1}</span>
              <h3 className="mt-2 font-semibold">{name}</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>
            </div>
          ))}
        </div>
        <p className="mt-5 text-xs text-slate-500">
          Questions use focused source retrieval. The council and trial views expose separate agent analysis and debate results.
        </p>
      </section>
    </div>
  );
}
