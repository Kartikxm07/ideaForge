"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  CalendarDays,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  FileText,
  GitBranch,
  LogOut,
  Play,
  RefreshCw,
  Scale,
  ShieldCheck,
  Swords,
  UploadCloud,
  Users,
} from "lucide-react";
import {
  odinApi,
  type OdinCitation,
  type OdinContract,
  type OdinGraph,
  type OdinRun,
  type OdinSession,
} from "@/lib/odin-api";
import { TrialView } from "@/components/views/TrialView";

type View = "trial" | "debate" | "exposure" | "graph" | "time" | "actions";
const navigation: {
  id: View;
  label: string;
  icon: typeof GitBranch;
  code: string;
}[] = [
  { id: "trial", label: "Agent Trial Chamber", icon: Swords, code: "FR7.2" },
  { id: "debate", label: "Agent Debate", icon: Users, code: "FR9.4" },
  {
    id: "exposure",
    label: "Exposure Views",
    icon: CircleDollarSign,
    code: "FR7.3",
  },
  { id: "graph", label: "Contract Graph", icon: GitBranch, code: "FR9.1" },
  { id: "time", label: "Time Simulator", icon: Clock3, code: "FR9.2" },
  { id: "actions", label: "Alerts & Actions", icon: Bell, code: "FR9.5" },
];
const emptyRun: OdinRun = {
  status: "NOT_RUN",
  extractions: [],
  timeline: [],
  findings: [],
  verifications: [],
  rulings: [],
  messages: [],
};
const addDays = (days: number) =>
  new Date(Date.UTC(2027, 0, 15 + days)).toISOString().slice(0, 10);
const daysBetween = (from: string, to: string) =>
  Math.round(
    (Date.parse(to + "T00:00:00Z") - Date.parse(from + "T00:00:00Z")) /
      86400000,
  );

function Citation({ citation }: { citation: OdinCitation }) {
  return (
    <details className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
      <summary className="cursor-pointer font-semibold text-[#284669]">
        {citation.document_key} · {citation.clause_ref}
      </summary>
      <blockquote className="mt-2 border-l-2 border-[#d4a017] pl-3 text-slate-600">
        “{citation.quote}”
      </blockquote>
      <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px] text-slate-500">
        {citation.chunk_id && (
          <span className="rounded bg-white px-1.5 py-1">
            chunk {citation.chunk_id}
          </span>
        )}
        {citation.page_num && (
          <span className="rounded bg-white px-1.5 py-1">
            page {citation.page_num}
          </span>
        )}
        {citation.content_sha256 && (
          <span className="rounded bg-white px-1.5 py-1">
            sha256 {citation.content_sha256.slice(0, 12)}…
          </span>
        )}
      </div>
      <a
        href={`/api/v1/workspace/contracts/${encodeURIComponent(citation.document_key)}/source`}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-block font-semibold text-[#276090] underline"
      >
        Open source document
      </a>
    </details>
  );
}

function Empty({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/70 p-10 text-center">
      <FileText className="mx-auto text-slate-300" size={32} />
      <p className="mt-3 font-semibold text-[#1b3551]">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{detail}</p>
    </div>
  );
}

function GraphPanel({ graph }: { graph: OdinGraph }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [kind, setKind] = useState("all");
  const nodes = graph.nodes
    .filter((n) => kind === "all" || n.kind === kind)
    .slice(0, 36);
  const positions = useMemo(() => {
    const map: Record<string, { x: number; y: number }> = {};
    const groups = ["contract", "party", "clause", "risk"];
    for (const [column, group] of groups.entries()) {
      const items = graph.nodes.filter((n) => n.kind === group).slice(0, 12);
      items.forEach((node, index) => {
        map[node.id] = {
          x: 120 + column * 205,
          y: 60 + (index + 1) * (360 / (items.length + 1)),
        };
      });
    }
    return map;
  }, [graph.nodes]);
  const chosen = graph.nodes.find((n) => n.id === selected);
  const colors: Record<string, string> = {
    contract: "#17375b",
    party: "#3c75a5",
    clause: "#d4a017",
    risk: "#c94d56",
  };
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_280px]">
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-bold text-[#172f4d]">Contract relationships</h2>
            <p className="text-xs text-slate-500">
              {graph.nodes.length} sourced nodes · {graph.edges.length}{" "}
              connections
            </p>
          </div>
          <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
            {["all", "contract", "party", "clause", "risk"].map((value) => (
              <button
                key={value}
                onClick={() => setKind(value)}
                className={`rounded-md px-2.5 py-1.5 text-xs capitalize ${kind === value ? "bg-white font-semibold text-[#17375b] shadow-sm" : "text-slate-500"}`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>
        {nodes.length ? (
          <div className="mt-4 overflow-x-auto rounded-lg bg-[#f7fafd]">
            <svg
              viewBox="0 0 850 450"
              className="h-[450px] min-w-[720px] w-full"
              role="img"
              aria-label="Interactive graph of contracts, parties, clauses and risks"
            >
              {graph.edges.map((edge) => {
                const a = positions[edge.source],
                  b = positions[edge.target];
                return a &&
                  b &&
                  nodes.some((n) => n.id === edge.source) &&
                  nodes.some((n) => n.id === edge.target) ? (
                  <line
                    key={edge.id}
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke={edge.label === "Cites" ? "#d5a33b" : "#c7d4e2"}
                    strokeWidth="2"
                  />
                ) : null;
              })}
              {nodes.map((node) => {
                const p = positions[node.id];
                return p ? (
                  <g
                    key={node.id}
                    onClick={() => setSelected(node.id)}
                    className="cursor-pointer"
                    tabIndex={0}
                    role="button"
                    aria-label={`Inspect ${node.label}`}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") setSelected(node.id);
                    }}
                  >
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={selected === node.id ? 15 : 11}
                      fill={colors[node.kind] || "#74869a"}
                      stroke="#fff"
                      strokeWidth="3"
                    />
                    <text
                      x={p.x + 17}
                      y={p.y + 4}
                      fill="#263e59"
                      fontSize="10"
                      fontWeight="600"
                    >
                      {node.label.slice(0, 23)}
                    </text>
                  </g>
                ) : null;
              })}
            </svg>
          </div>
        ) : (
          <div className="mt-5">
            <Empty
              title="No contracts in this workspace"
              detail="Upload a text contract in Organization settings to start the graph."
            />
          </div>
        )}
      </div>
      <aside className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="font-bold">Node details</h3>
        {chosen ? (
          <div className="mt-5 space-y-3">
            <span className="rounded-full bg-[#eaf2fa] px-2.5 py-1 text-xs font-semibold capitalize text-[#284669]">
              {chosen.kind}
            </span>
            <p className="break-words text-sm font-semibold">{chosen.label}</p>
            <p className="text-xs text-slate-500">
              Connected to{" "}
              {
                graph.edges.filter(
                  (e) => e.source === chosen.id || e.target === chosen.id,
                ).length
              }{" "}
              nodes
            </p>
            {graph.edges
              .filter((e) => e.source === chosen.id || e.target === chosen.id)
              .map((e) => (
                <p
                  key={e.id}
                  className="rounded-lg bg-slate-50 px-3 py-2 text-xs"
                >
                  {e.label}:{" "}
                  {graph.nodes.find(
                    (n) =>
                      n.id === (e.source === chosen.id ? e.target : e.source),
                  )?.label || "Source"}
                </p>
              ))}
          </div>
        ) : (
          <p className="mt-5 text-sm text-slate-500">
            Select a node to inspect its relationships.
          </p>
        )}
      </aside>
    </div>
  );
}

function TimePanel({
  run,
  day,
  setDay,
}: {
  run: OdinRun;
  day: number;
  setDay: (value: number) => void;
}) {
  const current = addDays(day);
  const rows = [...run.timeline].sort((a, b) => a.date.localeCompare(b.date));
  const overdue = rows.filter((r) => r.date < current).length;
  const upcoming = rows.filter((r) => r.date >= current).length;
  const dateLinkedRisks = run.findings.filter((f) =>
    f.citations.some((c) =>
      rows.some(
        (r) =>
          r.document_key === c.document_key &&
          r.citation.clause_ref === c.clause_ref &&
          r.date <= current,
      ),
    ),
  ).length;
  const penaltyTriggers = rows.filter(
    (r) =>
      r.date <= current &&
      run.extractions.some(
        (t) =>
          t.document_key === r.document_key &&
          t.citation.clause_ref === r.citation.clause_ref &&
          /penalt|late fee|liquidated damages/i.test(t.field + " " + t.value),
      ),
  ).length;
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-bold">Simulated clock</h2>
            <p className="text-xs text-slate-500 mt-1">
              Move the date to reclassify cited obligations and deadlines.
            </p>
          </div>
          <div className="rounded-lg border border-[#d6e2ef] bg-[#f4f8fc] px-3 py-2 text-sm font-semibold text-[#17375b]">
            <CalendarDays size={16} className="mr-2 inline" />
            {current}
          </div>
        </div>
        <input
          aria-label="Simulated date"
          type="range"
          min="0"
          max="365"
          value={day}
          onChange={(e) => setDay(Number(e.target.value))}
          className="mt-8 w-full accent-[#17375b]"
        />
        <div className="mt-2 flex justify-between text-xs text-slate-400">
          <span>15 Jan 2027</span>
          <span>15 Jan 2028</span>
        </div>
        <div className="mt-5 flex gap-2">
          {[0, 49, 137, 243].map((value) => (
            <button
              key={value}
              onClick={() => setDay(value)}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50"
            >
              {addDays(value)}
            </button>
          ))}
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Past deadlines", overdue, "text-[#bd4550]"],
          ["Upcoming", upcoming, "text-[#17375b]"],
          ["Date linked risks", dateLinkedRisks, "text-[#bd8a1e]"],
          ["Penalty terms reached", penaltyTriggers, "text-[#bd4550]"],
        ].map(([label, number, color]) => (
          <div
            key={label}
            className="rounded-xl border border-slate-200 bg-white p-5"
          >
            <p className="text-xs text-slate-500">{label}</p>
            <p className={`mt-2 text-3xl font-bold ${color}`}>{number}</p>
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="font-bold">Obligation timeline</h3>
        {rows.length ? (
          <div className="mt-4 divide-y divide-slate-100">
            {rows.map((row) => (
              <div
                key={row.id}
                className="grid gap-3 py-4 sm:grid-cols-[100px_90px_1fr]"
              >
                <span className="text-xs font-semibold text-[#17375b]">
                  {row.date}
                </span>
                <span
                  className={`w-fit h-fit rounded-full px-2 py-1 text-[11px] font-semibold ${row.date < current ? "bg-red-50 text-red-700" : "bg-blue-50 text-blue-700"}`}
                >
                  {row.date < current
                    ? "Past"
                    : `${daysBetween(current, row.date)} days`}
                </span>
                <div>
                  <p className="text-sm font-medium">{row.description}</p>
                  <Citation citation={row.citation} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-4">
            <Empty
              title="No dated obligations extracted"
              detail="Run the agents on contracts with explicit dates. The slider is ready; dates are never guessed from general terms."
            />
          </div>
        )}
      </div>
    </div>
  );
}

function ExposurePanel({
  run,
  contracts,
  current,
}: {
  run: OdinRun;
  contracts: OdinContract[];
  current: string;
}) {
  const [heatmapBy, setHeatmapBy] = useState<"contract" | "clause">("contract");
  const months = Array.from({ length: 6 }, (_, i) =>
    new Date(Date.UTC(2027, i, 1)).toISOString().slice(0, 7),
  );
  const sourceAmounts = run.extractions.filter((t) =>
    /\$\s?\d[\d,]*(?:\.\d{2})?/.test(t.citation.quote),
  );
  const scenario = run.scenarios?.[run.scenarios.length - 1];
  const heatmapRows =
    heatmapBy === "contract"
      ? contracts.map((c) => ({
          key: c.document_key,
          label: c.document_key,
          items: run.timeline.filter((t) => t.document_key === c.document_key),
        }))
      : Array.from(new Set(run.extractions.map((t) => t.field)))
          .slice(0, 12)
          .map((field) => ({
            key: field,
            label: field,
            items: run.timeline.filter((t) =>
              run.extractions.some(
                (x) =>
                  x.field === field &&
                  x.document_key === t.document_key &&
                  x.citation.clause_ref === t.citation.clause_ref,
              ),
            ),
          }));
  return (
    <div className="space-y-5">
      {scenario && (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5">
          <h2 className="font-bold text-[#17375b]">
            Norns · conditional worst case
          </h2>
          <p className="mt-2 text-sm text-slate-700">{scenario.summary}</p>
          <p className="mt-2 text-xs text-slate-500">{scenario.limitation}</p>
        </section>
      )}
      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="font-bold">Financial exposure</h2>
          <div className="mx-auto mt-7 flex h-48 w-48 items-center justify-center rounded-full border-[18px] border-slate-100 border-t-[#d4a017]">
            <div className="text-center">
              <CircleDollarSign className="mx-auto text-[#d4a017]" size={26} />
              <p className="mt-2 text-lg font-bold">Unquantified</p>
              <p className="text-xs text-slate-500">Verified formula pending</p>
            </div>
          </div>
          <p className="mt-6 text-xs leading-5 text-slate-500">
            A contract amount alone is not exposure. ODIN needs event evidence,
            applicable terms, and a deterministic calculation before showing a
            currency total.
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="font-bold">Risk heatmap</h2>
              <p className="mt-1 text-xs text-slate-500">
                Cited dated obligations by {heatmapBy} and month · simulated{" "}
                {current}
              </p>
            </div>
            <select
              aria-label="Group heatmap"
              value={heatmapBy}
              onChange={(e) =>
                setHeatmapBy(e.target.value as "contract" | "clause")
              }
              className="rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
            >
              <option value="contract">By contract</option>
              <option value="clause">By clause type</option>
            </select>
          </div>
          {heatmapRows.length ? (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    <th className="pb-3 text-left">
                      {heatmapBy === "contract" ? "Contract" : "Clause type"}
                    </th>
                    {months.map((month) => (
                      <th key={month} className="px-2 pb-3 text-center">
                        {month.slice(5)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heatmapRows.map((row) => (
                    <tr key={row.key} className="border-t border-slate-100">
                      <td className="py-3 pr-4 font-medium capitalize">
                        {row.label}
                      </td>
                      {months.map((month) => {
                        const count = row.items.filter((t) =>
                          t.date.startsWith(month),
                        ).length;
                        return (
                          <td key={month} className="p-1 text-center">
                            <span
                              className={`inline-flex h-9 w-9 items-center justify-center rounded-md ${count ? "bg-[#eec76b] text-[#503500] font-bold" : "bg-slate-50 text-slate-300"}`}
                            >
                              {count || "·"}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="mt-4">
              <Empty
                title="No heatmap data"
                detail="Upload and analyze contracts to populate the heatmap."
              />
            </div>
          )}
        </div>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="font-bold">Cited monetary terms</h3>
        <p className="mt-1 text-xs text-slate-500">
          Amounts found in verified source quotes. These are reference terms,
          not summed liabilities.
        </p>
        {sourceAmounts.length ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {sourceAmounts.map((term) => (
              <div
                key={term.id}
                className="rounded-lg border border-slate-100 p-3"
              >
                <p className="text-sm font-semibold">
                  {term.document_key} · {term.field}
                </p>
                <p className="mt-1 text-xs text-slate-600">{term.value}</p>
                <Citation citation={term.citation} />
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-5 text-sm text-slate-500">
            No verified monetary terms yet.
          </p>
        )}
      </div>
    </div>
  );
}

function DebatePanel({ run }: { run: OdinRun }) {
  const live = run.status === "QUEUED" || run.status === "RUNNING";
  const latest = run.messages.at(-1);
  const thorFeed = run.messages.filter((m) => m.from === "Thor").slice(-8);
  const heimdallFeed = run.messages
    .filter((m) => m.from === "Heimdall" || m.to === "Heimdall")
    .slice(-8);
  return (
    <div className="space-y-5">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-5"
      >
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full ${live ? "bg-emerald-500" : "bg-slate-300"}`}
            />
            <h2 className="font-bold">ODIN Evidence Arena · {run.status}</h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {latest
              ? `${latest.from} → ${latest.to}: ${latest.message}`
              : "Waiting for an agent handoff."}
          </p>
        </div>
        <a
          href="/thor/"
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg bg-[#17375b] px-3 py-2 text-xs font-semibold text-white"
        >
          Open Thor proof vault
        </a>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <AgentLane
          title="Thor · verified chunks"
          tone="blue"
          count={run.extractions.length}
          items={thorFeed}
          empty="Thor is preparing cited chunks."
        />
        <AgentLane
          title="Loki ↔ Heimdall"
          tone="emerald"
          count={run.verifications.length}
          items={heimdallFeed}
          empty="The evidence challenge has not started."
        />
        <AgentLane
          title="Tyr · rulings"
          tone="amber"
          count={run.rulings.length}
          items={run.messages
            .filter((m) => m.from === "Tyr" || m.to === "Tyr")
            .slice(-8)}
          empty="Tyr is waiting for verified arguments."
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          {run.findings.length ? (
            run.findings.map((finding) => {
              const check = run.verifications
                .filter((v) => v.finding_id === finding.id)
                .slice(-1)[0];
              const ruling = run.rulings.find(
                (r) => r.finding_id === finding.id,
              );
              return (
                <article
                  key={finding.id}
                  className="rounded-xl border border-slate-200 bg-white p-5"
                >
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-orange-50 px-2 py-1 text-xs font-bold text-orange-700">
                      Loki
                    </span>
                    <span className="text-xs capitalize text-slate-500">
                      {finding.severity}
                    </span>
                  </div>
                  <h3 className="mt-3 font-semibold">{finding.claim}</h3>
                  <p className="mt-1 text-sm text-slate-600">
                    {finding.reasoning}
                  </p>
                  {finding.citations.map((cite, i) => (
                    <Citation key={i} citation={cite} />
                  ))}
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-lg bg-emerald-50 p-3">
                      <p className="text-xs font-bold text-emerald-800">
                        Heimdall · {check?.verdict || "Pending"}
                      </p>
                      <p className="mt-1 text-xs text-emerald-950">
                        {check?.reason || "Verification has not completed."}
                      </p>
                    </div>
                    <div className="rounded-lg bg-blue-50 p-3">
                      <p className="text-xs font-bold text-blue-800">
                        Tyr · {ruling?.outcome || "Pending"}
                      </p>
                      <p className="mt-1 text-xs text-blue-950">
                        {ruling?.rationale || "No ruling yet."}
                      </p>
                    </div>
                  </div>
                </article>
              );
            })
          ) : (
            <Empty
              title="No debated findings yet"
              detail="Run the agents after uploading contracts. Claims appear only with verified source citations."
            />
          )}
        </div>
        <aside className="rounded-xl border border-slate-200 bg-white p-5 h-fit">
          <h3 className="font-bold">Persisted handoffs</h3>
          <div className="mt-4 space-y-4">
            {run.messages.length ? (
              run.messages.map((message) => (
                <div
                  key={message.id}
                  className="border-l-2 border-[#d4a017] pl-3"
                >
                  <p className="text-xs font-bold">
                    {message.from} <ArrowRight className="inline" size={11} />{" "}
                    {message.to}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {message.message}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">
                Handoffs appear as agents work.
              </p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function AgentLane({
  title,
  tone,
  count,
  items,
  empty,
}: {
  title: string;
  tone: "blue" | "emerald" | "amber";
  count: number;
  items: OdinRun["messages"];
  empty: string;
}) {
  const colors = {
    blue: "border-blue-200 bg-blue-50 text-blue-900",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-900",
    amber: "border-amber-200 bg-amber-50 text-amber-950",
  };
  return (
    <section className={`min-h-44 rounded-xl border p-4 ${colors[tone]}`}>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-bold">{title}</h3>
        <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs font-bold">
          {count}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {items.length ? (
          items.map((item) => (
            <div
              key={item.id}
              className="rounded-lg bg-white/80 p-2.5 text-xs shadow-sm"
            >
              <p className="font-bold">
                {item.from} <ArrowRight className="inline" size={10} />{" "}
                {item.to}
              </p>
              <p className="mt-1 line-clamp-3 opacity-75">{item.message}</p>
            </div>
          ))
        ) : (
          <p className="text-xs opacity-65">{empty}</p>
        )}
      </div>
    </section>
  );
}

type OdinEvent = {
  event_id: string;
  occurred_at: string;
  channel: string;
  sender: string;
  recipient: string;
  subject: string;
  body: string;
};
type AnchorResult = {
  status: string;
  sha256: string;
  transaction_hash?: string;
  explorer_url?: string;
  block_number?: number;
  confirmations?: number;
  evidence_matches?: boolean;
};

function ThorAnchorCard({ run }: { run: OdinRun }) {
  const [anchor, setAnchor] = useState<AnchorResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function act(action: "prepare" | "submit" | "receipt") {
    if (!run.id) return;
    setBusy(true);
    setError("");
    try {
      setAnchor(
        await odinApi<AnchorResult>(
          `/workspace/agents/runs/${encodeURIComponent(run.id)}/anchor/${action}`,
          { method: action === "receipt" ? "GET" : "POST" },
        ),
      );
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Anchor operation failed",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="font-bold">Thor evidence anchor · Sepolia</h2>
      <p className="mt-1 text-xs text-slate-500">
        Hashes Thor’s local chunks and verified facts. Contract text stays
        local; only the SHA-256 digest is submitted.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          disabled={busy || !run.id}
          onClick={() => act("prepare")}
          className="rounded-lg border border-[#17375b] px-3 py-2 text-xs font-semibold text-[#17375b] disabled:opacity-50"
        >
          Prepare digest
        </button>
        <button
          disabled={busy || !anchor}
          onClick={() => act("submit")}
          className="rounded-lg bg-[#17375b] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          Submit to Sepolia
        </button>
        <button
          disabled={busy || !anchor?.transaction_hash}
          onClick={() => act("receipt")}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold disabled:opacity-50"
        >
          Verify receipt
        </button>
      </div>
      {anchor && (
        <div className="mt-4 break-all rounded-lg bg-slate-50 p-3 font-mono text-xs">
          <p>Status: {anchor.status}</p>
          <p>SHA-256: {anchor.sha256}</p>
          {anchor.transaction_hash && (
            <p>Transaction: {anchor.transaction_hash}</p>
          )}
          {anchor.block_number !== undefined && (
            <p>
              Block: {anchor.block_number} · Confirmations:{" "}
              {anchor.confirmations} · Evidence matches:{" "}
              {String(anchor.evidence_matches)}
            </p>
          )}
          {anchor.explorer_url && (
            <a
              className="mt-2 inline-block text-[#276090] underline"
              href={anchor.explorer_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open Sepolia receipt
            </a>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="mt-3 text-xs text-red-700">
          {error}
        </p>
      )}
    </section>
  );
}

function EmailDraftCard({
  draft,
  refresh,
}: {
  draft: NonNullable<OdinRun["email_drafts"]>[number];
  refresh: () => Promise<void>;
}) {
  const [recipient, setRecipient] = useState(draft.recipient || "");
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function act(action: "approve" | "send") {
    setBusy(true);
    setError("");
    try {
      await odinApi(
        `/workspace/agents/email-drafts/${encodeURIComponent(draft.id)}/${action}`,
        action === "approve"
          ? {
              method: "POST",
              body: JSON.stringify({ recipient, subject, body }),
            }
          : { method: "POST" },
      );
      await refresh();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not update alert",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold">Email alert draft</h4>
        <span className="text-xs font-bold text-[#284669]">{draft.status}</span>
      </div>
      <label className="mt-3 block text-xs font-semibold">
        To
        <input
          type="email"
          value={recipient}
          onChange={(event) => setRecipient(event.target.value)}
          disabled={draft.status !== "DRAFT"}
          className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm disabled:bg-slate-100"
        />
      </label>
      <label className="mt-3 block text-xs font-semibold">
        Subject
        <input
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          disabled={draft.status !== "DRAFT"}
          className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm disabled:bg-slate-100"
        />
      </label>
      <label className="mt-3 block text-xs font-semibold">
        Message
        <textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          disabled={draft.status !== "DRAFT"}
          rows={7}
          className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm disabled:bg-slate-100"
        />
      </label>
      {error && (
        <p role="alert" className="mt-2 text-xs text-red-700">
          {error}
        </p>
      )}
      {draft.status === "DRAFT" && (
        <button
          disabled={busy || !recipient || !subject || !body}
          onClick={() => act("approve")}
          className="mt-3 rounded-lg bg-[#17375b] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          Approve alert
        </button>
      )}
      {draft.status === "APPROVED" && (
        <button
          disabled={busy}
          onClick={() => act("send")}
          className="mt-3 rounded-lg bg-[#17375b] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          Send with Resend
        </button>
      )}
      {draft.status === "SENT" && (
        <p className="mt-3 text-xs text-emerald-700">
          Sent {draft.sent_at?.slice(0, 16)}
        </p>
      )}
    </article>
  );
}

function ActionsPanel({
  run,
  current,
  events,
  refresh,
}: {
  run: OdinRun;
  current: string;
  events: OdinEvent[];
  refresh: () => Promise<void>;
}) {
  const [showEventForm, setShowEventForm] = useState(false);
  const [eventDate, setEventDate] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [eventError, setEventError] = useState("");
  async function addEvent() {
    setEventError("");
    try {
      await odinApi("/workspace/events", {
        method: "POST",
        body: JSON.stringify({
          event_id: `WEB-${Date.now()}`,
          timestamp: new Date(eventDate).toISOString(),
          channel: "manual",
          from: "Workspace user",
          to: "ODIN",
          subject,
          body,
        }),
      });
      setShowEventForm(false);
      setEventDate("");
      setSubject("");
      setBody("");
      await refresh();
    } catch (cause) {
      setEventError(
        cause instanceof Error ? cause.message : "Could not save event",
      );
    }
  }
  const deadlineAlerts = run.timeline
    .filter((t) => t.date >= current && daysBetween(current, t.date) <= 30)
    .map((t) => ({
      id: t.id,
      title: t.description,
      date: t.date,
      type: "Deadline",
      citation: t.citation,
    }));
  const riskAlerts = run.findings
    .filter(
      (f) =>
        run.verifications.filter((v) => v.finding_id === f.id).slice(-1)[0]
          ?.verdict === "confirmed",
    )
    .map((f) => ({
      id: f.id,
      title: f.claim,
      date: "",
      type: f.severity,
      citation: f.citations[0],
    }));
  const alerts = [...riskAlerts, ...deadlineAlerts].sort(
    (a, b) =>
      (({ critical: 0, high: 1, medium: 2, low: 3 })[
        a.type.toLowerCase() as "critical" | "high" | "medium" | "low"
      ] ?? 4) -
      ({ critical: 0, high: 1, medium: 2, low: 3 }[
        b.type.toLowerCase() as "critical" | "high" | "medium" | "low"
      ] ?? 4),
  );
  const drafts = run.rulings.filter((r) => r.draft_notice);
  return (
    <div className="space-y-5">
      <ThorAnchorCard run={run} />
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="font-bold">Resend alert drafts</h2>
        <p className="mt-1 text-xs text-slate-500">
          Heimdall-confirmed risks are drafted here. An administrator reviews
          the message and recipient before delivery.
        </p>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {run.email_drafts?.length ? (
            run.email_drafts.map((draft) => (
              <EmailDraftCard key={draft.id} draft={draft} refresh={refresh} />
            ))
          ) : (
            <p className="text-sm text-slate-500">
              No verified alert drafts yet.
            </p>
          )}
        </div>
      </section>
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="font-bold">Prioritized alerts</h2>
          <p className="mt-1 text-xs text-slate-500">
            Cited findings and deadlines within 30 days of {current}.
          </p>
          <div className="mt-4 space-y-3">
            {alerts.length ? (
              alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="rounded-lg border border-slate-100 p-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="rounded-full bg-amber-50 px-2 py-1 text-[11px] font-bold capitalize text-amber-800">
                      {alert.type}
                    </span>
                    <span className="text-xs text-slate-500">{alert.date}</span>
                  </div>
                  <p className="mt-2 text-sm font-semibold">{alert.title}</p>
                  {alert.citation && <Citation citation={alert.citation} />}
                </div>
              ))
            ) : (
              <Empty
                title="No actionable alerts"
                detail="Alerts appear when agents find cited risks or upcoming deadlines."
              />
            )}
          </div>
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="font-bold">Draft notices</h2>
          <p className="mt-1 text-xs text-slate-500">
            Tyr drafts require human approval before any delivery.
          </p>
          <div className="mt-4 space-y-3">
            {drafts.length ? (
              drafts.map((ruling) => (
                <article
                  key={ruling.id}
                  className="rounded-lg border border-slate-100 p-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="rounded-full bg-blue-50 px-2 py-1 text-[11px] font-bold text-blue-800">
                      Review draft
                    </span>
                    <span className="text-xs text-slate-500">
                      {ruling.outcome}
                    </span>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {ruling.draft_notice}
                  </p>
                  {ruling.citations.map((cite, index) => (
                    <Citation key={index} citation={cite} />
                  ))}
                </article>
              ))
            ) : (
              <Empty
                title="No drafted notices"
                detail="A draft appears only after a cited finding is verified and upheld."
              />
            )}
          </div>
        </section>
      </div>
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-bold">Operational event feed</h2>
            <p className="mt-1 text-xs text-slate-500">
              Recorded events are available to Heimdall in the next agent run.
            </p>
          </div>
          <button
            onClick={() => setShowEventForm(!showEventForm)}
            className="rounded-lg bg-[#17375b] px-3 py-2 text-xs font-semibold text-white"
          >
            Add event
          </button>
        </div>
        {showEventForm && (
          <div className="mt-5 grid gap-3 rounded-lg bg-slate-50 p-4">
            <label className="text-xs font-semibold">
              When
              <input
                type="datetime-local"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-200 p-2"
              />
            </label>
            <label className="text-xs font-semibold">
              Subject
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-200 p-2"
              />
            </label>
            <label className="text-xs font-semibold">
              Details
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-200 p-2"
                rows={3}
              />
            </label>
            {eventError && (
              <p role="alert" className="text-xs text-red-700">
                {eventError}
              </p>
            )}
            <button
              disabled={!eventDate || !subject || !body}
              onClick={addEvent}
              className="rounded-lg bg-[#d4a017] px-4 py-2 text-xs font-bold text-white disabled:opacity-50"
            >
              Save event
            </button>
          </div>
        )}
        <div className="mt-4 space-y-2">
          {events.length ? (
            events.map((event) => (
              <div
                key={event.event_id}
                className="rounded-lg border border-slate-100 p-3"
              >
                <p className="text-xs text-slate-500">
                  {event.occurred_at.slice(0, 16).replace("T", " ")} ·{" "}
                  {event.channel}
                </p>
                <p className="mt-1 text-sm font-semibold">{event.subject}</p>
                <p className="mt-1 text-xs text-slate-600">{event.body}</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">No events recorded.</p>
          )}
        </div>
      </section>
    </div>
  );
}

export default function WarRoomPage() {
  const router = useRouter();
  const [view, setView] = useState<View>("trial");
  const [session, setSession] = useState<OdinSession | null>(null);
  const [contracts, setContracts] = useState<OdinContract[]>([]);
  const [graph, setGraph] = useState<OdinGraph>({ nodes: [], edges: [] });
  const [events, setEvents] = useState<OdinEvent[]>([]);
  const [run, setRun] = useState<OdinRun>(emptyRun);
  const [day, setDay] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [identity, list, network, latest, eventRows] = await Promise.all([
        odinApi<OdinSession>("/auth/session"),
        odinApi<{ items: OdinContract[] }>(
          "/workspace/contracts?page_size=100",
        ),
        odinApi<OdinGraph>("/workspace/graph"),
        odinApi<OdinRun>("/workspace/agents/runs/latest"),
        odinApi<OdinEvent[]>("/workspace/events"),
      ]);
      setSession(identity);
      setContracts(list.items);
      setGraph(network);
      setRun(latest);
      setEvents(eventRows);
      setError("");
    } catch (cause) {
      if (cause instanceof Error && /Session expired/.test(cause.message))
        router.replace("/login");
      else
        setError(
          cause instanceof Error ? cause.message : "Could not load ODIN",
        );
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    if (run.status !== "QUEUED" && run.status !== "RUNNING") return;
    const stream = new EventSource("/api/v1/workspace/stream", {
      withCredentials: true,
    });
    stream.addEventListener("update", () => void refresh());
    stream.addEventListener("expired", () => router.replace("/login"));
    const fallback = setInterval(() => void refresh(), 10000);
    return () => {
      stream.close();
      clearInterval(fallback);
    };
  }, [run.status, refresh, router]);

  async function launch() {
    setError("");
    try {
      await odinApi("/workspace/agents/run", {
        method: "POST",
        body: JSON.stringify({
          document_keys: contracts
            .filter((c) => !c.warning)
            .map((c) => c.document_key),
        }),
      });
      await refresh();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not start agents",
      );
    }
  }
  async function logout() {
    await odinApi("/auth/logout", { method: "POST" });
    router.push("/login");
  }
  const org =
    session?.organizations.find((o) => o.id === session.organization_id)
      ?.name || "Your organization";
  const current = addDays(day);
  const eligibleCount = contracts.filter((c) => !c.warning).length;

  return (
    <div className="min-h-screen bg-[#edf3f9] text-[#10243d]">
      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-[#dce5ee] bg-white px-5 lg:px-8">
        <div className="flex items-center gap-3">
          <span className="text-3xl leading-none text-[#d4a017]">◭</span>
          <div>
            <b className="text-lg tracking-tight">ODIN</b>
            <p className="text-[10px] text-slate-500">CONTRACT INTELLIGENCE</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline text-xs font-semibold text-slate-500">
            {org}
          </span>
          <button
            onClick={refresh}
            aria-label="Refresh dashboard"
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"
          >
            <RefreshCw size={17} />
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-[#17375b]"
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </header>
      <div className="mx-auto flex max-w-[1650px]">
        <aside className="hidden min-h-[calc(100vh-64px)] w-60 shrink-0 border-r border-[#dce5ee] bg-white p-4 md:block">
          <p className="px-3 pt-4 text-[10px] font-bold uppercase tracking-[.2em] text-slate-400">
            War room
          </p>
          <nav className="mt-4 space-y-1">
            {navigation.map((item) => (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm ${view === item.id ? "bg-[#17375b] font-semibold text-white" : "text-[#49627c] hover:bg-slate-100"}`}
              >
                <item.icon size={17} />
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
          <div className="mt-10 rounded-xl border border-[#e6e0ce] bg-[#fffbf0] p-4">
            <p className="text-xs font-bold text-[#8c651b]">Agent run</p>
            <p className="mt-2 text-sm font-semibold capitalize">
              {run.status.toLowerCase().replace("_", " ")}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {run.extractions.length} terms · {run.findings.length} findings
            </p>
          </div>
          <button
            onClick={() => router.push("/onboarding")}
            className="mt-6 flex items-center gap-2 px-3 text-xs font-semibold text-[#49627c] hover:text-[#17375b]"
          >
            <UploadCloud size={16} /> Organization & uploads
          </button>
        </aside>
        <main className="min-w-0 flex-1 p-5 lg:p-8">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.16em] text-[#b68928]">
                {org} · War room
              </p>
              <h1 className="mt-1 text-3xl font-bold">
                Welcome, {session?.user.name || "there"}
              </h1>
              <p className="mt-2 text-sm text-[#63778d]">
                Five connected views of your contracts, timeline, risks, agent
                decisions, and actions.
              </p>
            </div>
            <button
              disabled={
                !eligibleCount ||
                run.status === "RUNNING" ||
                run.status === "QUEUED"
              }
              onClick={launch}
              className="flex items-center gap-2 rounded-lg bg-[#17375b] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#234b75] disabled:opacity-50"
            >
              <Play size={16} />
              {run.status === "RUNNING" || run.status === "QUEUED"
                ? "Agents running…"
                : "Run five agents"}
            </button>
          </div>
          {error && (
            <p
              role="alert"
              className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              {error}
            </p>
          )}
          {contracts
            .filter((c) => c.warning)
            .map((c) => (
              <p
                key={c.document_key}
                role="status"
                className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
              >
                <b>{c.title}:</b> {c.warning}{" "}
                <button
                  onClick={() => router.push("/onboarding")}
                  className="ml-2 font-semibold underline"
                >
                  Upload a contract
                </button>
              </p>
            ))}
          {run.status === "INCOMPLETE" &&
            !contracts.some(
              (c) => c.warning && run.error?.startsWith(`${c.document_key}:`),
            ) && (
              <p
                role="status"
                className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
              >
                Agent run incomplete: {run.error || "One stage failed"}. Earlier
                verified outputs remain visible.
              </p>
            )}
          <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ["Contracts", contracts.length, FileText],
              ["Verified terms", run.extractions.length, ShieldCheck],
              ["Findings", run.findings.length, AlertTriangle],
              [
                "Draft actions",
                run.rulings.filter((r) => r.draft_notice).length,
                Scale,
              ],
            ].map(([label, value, Icon]) => {
              const Pictogram = Icon as typeof FileText;
              return (
                <div
                  key={label as string}
                  className="rounded-xl border border-[#dce5ee] bg-white p-4 shadow-sm"
                >
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                    <span>{label as string}</span>
                    <Pictogram size={17} className="text-[#d4a017]" />
                  </div>
                  <p className="mt-2 text-2xl font-bold">{value as number}</p>
                </div>
              );
            })}
          </div>
          <div className="mb-5 flex gap-2 overflow-x-auto pb-1 md:hidden">
            {navigation.map((item) => (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                className={`shrink-0 rounded-lg px-3 py-2 text-xs font-semibold ${view === item.id ? "bg-[#17375b] text-white" : "bg-white text-[#49627c]"}`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="mb-5 flex items-center gap-2 text-sm">
            <span className="rounded-md bg-[#e9f0f7] px-2 py-1 text-xs font-bold text-[#2b587f]">
              {navigation.find((n) => n.id === view)?.code}
            </span>
            <ChevronRight size={14} className="text-slate-400" />
            <span className="font-semibold">
              {navigation.find((n) => n.id === view)?.label}
            </span>
            <span className="ml-auto text-xs text-slate-500">
              {loading
                ? "Loading…"
                : run.status === "NOT_RUN"
                  ? "Awaiting first analysis"
                  : `Run: ${run.status.toLowerCase()}`}
            </span>
          </div>
          {view === "trial" && <TrialView />}
          {view === "graph" && <GraphPanel graph={graph} />}
          {view === "time" && <TimePanel run={run} day={day} setDay={setDay} />}
          {view === "exposure" && (
            <ExposurePanel run={run} contracts={contracts} current={current} />
          )}
          {view === "debate" && <DebatePanel run={run} />}
          {view === "actions" && (
            <ActionsPanel
              run={run}
              current={current}
              events={events}
              refresh={refresh}
            />
          )}
        </main>
      </div>
    </div>
  );
}
