"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  DollarSign,
  AlertTriangle,
  Scale,
  Clock,
  FileCheck,
  ShieldCheck,
  Info,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  variant = "gold",
  delay = 0,
  tooltip,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ComponentType<{ className?: string }>;
  variant?: "gold" | "crimson" | "emerald" | "blue";
  delay?: number;
  tooltip?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className={`kpi-card kpi-${variant} group cursor-default`}
      title={tooltip}
    >
      <div className="flex items-start justify-between mb-3">
        <p className="label-caps text-[10px]">{label}</p>
        <div className="flex items-center gap-1">
          <Icon className={`w-3.5 h-3.5 ${
            variant === "crimson" ? "text-[#C0162C]" :
            variant === "emerald" ? "text-emerald-600" :
            variant === "blue"    ? "text-blue-600" :
            "text-amber-600"
          }`} />
          {tooltip && <Info className="w-3 h-3 text-[#8A7355] opacity-0 group-hover:opacity-100 transition-opacity" />}
        </div>
      </div>

      <p className={`font-bold text-2xl leading-none font-jetbrains tracking-tight ${
        variant === "crimson" ? "text-[#C0162C]" :
        variant === "emerald" ? "text-emerald-700" :
        variant === "blue"    ? "text-blue-700" :
        "text-[#92700A]"
      }`}>
        {value}
      </p>

      {sub && (
        <p className="text-[11px] text-[#8A7355] mt-1.5 font-medium truncate">{sub}</p>
      )}
    </motion.div>
  );
}

export function KpiStrip() {
  const { currentSnapshot, conflicts, alerts, actions } = useOdinStore();

  const openFindingsTotal =
    currentSnapshot.openFindingsCount.critical +
    currentSnapshot.openFindingsCount.high +
    currentSnapshot.openFindingsCount.medium +
    currentSnapshot.openFindingsCount.low;

  return (
    <section className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 stagger fade-in-up">
      <KpiCard
        label="Total Exposure"
        value={`$${currentSnapshot.totalExposure.toLocaleString("en-US")}`}
        sub="Gross: $88.5k · +18.2% delta"
        icon={DollarSign}
        variant="crimson"
        delay={0.03}
        tooltip="Sum of active contractual liabilities minus upstream recoveries"
      />
      <KpiCard
        label="Net Gap"
        value={`$${currentSnapshot.netUncoveredGap.toLocaleString("en-US")}`}
        sub="StratoNode vs Harbor SLA"
        icon={Scale}
        variant="gold"
        delay={0.06}
        tooltip="Difference between upstream credit cap and downstream penalty"
      />
      <KpiCard
        label={`Open Findings (${openFindingsTotal})`}
        value={`${conflicts.length}`}
        sub={`${currentSnapshot.openFindingsCount.critical} critical · ${currentSnapshot.openFindingsCount.high} high`}
        icon={AlertTriangle}
        variant="gold"
        delay={0.09}
      />
      <KpiCard
        label="Next Deadline"
        value={`T-${currentSnapshot.nextDeadlineDays}d`}
        sub={currentSnapshot.nextDeadlineLabel}
        icon={Clock}
        variant="blue"
        delay={0.12}
      />
      <KpiCard
        label="Actions in Queue"
        value={`${actions.filter((a) => a.needsApproval).length}`}
        sub="Pending sign-off"
        icon={FileCheck}
        variant="gold"
        delay={0.15}
      />
      <KpiCard
        label="Confidence"
        value={`${(currentSnapshot.avgConfidence * 100).toFixed(1)}%`}
        sub="Above 65% gate"
        icon={ShieldCheck}
        variant="emerald"
        delay={0.18}
      />
    </section>
  );
}
