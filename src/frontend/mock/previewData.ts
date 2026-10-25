// Compatibility data for the existing, explicitly labeled preview. Never use as API fallback.
import { MOCK_CONTRACTS, SAAS_PLATFORM_CLAUSES, TIMELINE_SWIMLANES } from "./odinData";
import type { AlertItem, CheckpointSnapshot, HeatmapCell } from "@/types/odin";

export const MOCK_CLAUSES = Array.from(new Map(
  [...SAAS_PLATFORM_CLAUSES, ...MOCK_CONTRACTS.flatMap(contract => contract.clauses ?? [])]
    .map(clause => [clause.id, clause])
).values());

export const MOCK_SWIMLANES = TIMELINE_SWIMLANES;
export const MOCK_HEATMAP: HeatmapCell[] = [];
export const MOCK_ALERTS: AlertItem[] = TIMELINE_SWIMLANES.flatMap(lane =>
  lane.milestones.map((milestone, index) => ({
    id: `preview-${lane.contractId}-${index}`,
    contractId: lane.contractId,
    title: milestone.label,
    dueDate: milestone.date,
    countdownDays: Math.ceil((Date.parse(milestone.date) - Date.parse("2026-11-15")) / 86400000),
    severity: milestone.type === "penalty" ? "HIGH" as const : "LOW" as const,
    source: "Deadline" as const,
    description: `Sample ${milestone.type} milestone for ${lane.contractTitle}`,
    acknowledged: false,
    snoozed: false,
  }))
);

// Restore the original repository's checkpoint fixtures, not production statistics.
export const MOCK_SNAPSHOTS: Record<CheckpointSnapshot["id"], CheckpointSnapshot & { activeEvents: string[]; simulatedAlertDelta: { alertsCount: number; exposureDelta: number } }> = {
  CP1: {
    id: "CP1",
    date: "2026-10-01",
    label: "Checkpoint 1 — Baseline Ingestion",
    totalExposure: 18500,
    netUncoveredGap: 18500,
    insuranceCoverage: 500000,
    openFindingsCount: { critical: 0, high: 1, medium: 2, low: 1 },
    awaitingApprovalCount: 1,
    avgConfidence: 0.94,
    nextDeadlineDays: 45,
    nextDeadlineLabel: "StratoNode Q3 Invoice Due",
    activeEvents: ["Initial 8 contracts ingested", "All SHA-256 hashes verified", "Payment ledger synced"],
    simulatedAlertDelta: { alertsCount: 3, exposureDelta: 18500 },
  },
  CP2: {
    id: "CP2",
    date: "2026-11-15",
    label: "Checkpoint 2 — Drop 1 (StratoNode Outage)",
    totalExposure: 60500,
    netUncoveredGap: 42000,
    insuranceCoverage: 500000,
    openFindingsCount: { critical: 1, high: 2, medium: 1, low: 2 },
    awaitingApprovalCount: 3,
    avgConfidence: 0.91,
    nextDeadlineDays: 3,
    nextDeadlineLabel: "Harbor Retail Cure Notice Expiring",
    activeEvents: [
      "StratoNode US-East 228min outage recorded",
      "Harbor Retail breach notice served",
      "Asymmetric SLA liability gap triggered",
    ],
    simulatedAlertDelta: { alertsCount: 5, exposureDelta: 42000 },
  },
  CP3: {
    id: "CP3",
    date: "2027-01-10",
    label: "Checkpoint 3 — Drop 2 (Adjudications & Renewals)",
    totalExposure: 88500,
    netUncoveredGap: 24500,
    insuranceCoverage: 1000000,
    openFindingsCount: { critical: 0, high: 1, medium: 2, low: 3 },
    awaitingApprovalCount: 2,
    avgConfidence: 0.96,
    nextDeadlineDays: 12,
    nextDeadlineLabel: "Harbor Q4 SOC2 Delivery",
    activeEvents: [
      "Tyr ruling enforced on StratoNode precedence",
      "Apex Systems IP assignment executed",
      "Chubb Cyber Policy bound for 2027",
    ],
    simulatedAlertDelta: { alertsCount: 2, exposureDelta: -17500 },
  },
};

