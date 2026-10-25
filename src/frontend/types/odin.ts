export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type AgentName = "Odin" | "Thor" | "Norns" | "Loki" | "Heimdall" | "Tyr";

export type CitationStatus = "EXACT" | "FUZZY" | "NOT_FOUND";

export type EvidenceType = "SOURCED" | "INFERRED" | "FLAGGED";

export type FindingStatus = "PROMOTED" | "CONTESTED" | "DISMISSED";

export interface Clause {
  id: string; // e.g. "A2-S4.2"
  contractId: string;
  contractTitle: string;
  section: string;
  heading: string;
  text: string;
  highlightSnippet?: string;
  type: "uptime" | "liability" | "notice" | "termination" | "payment" | "ip" | "amendment";
  confidence: number; // 0-1
  citationStatus: CitationStatus;
  evidenceType: EvidenceType;
  status: FindingStatus;
  scoreBreakdown: {
    citation: number; // 0-100
    confidence: number;
    agreement: number;
    external: number;
    composite: number; // 65% gate
  };
  provenance: {
    extractedBy: AgentName;
    timestamp: string;
    docOffset: number;
    contentHash: string;
  };
}

export interface ContractNode {
  id: string; // "STD", "A1", "A2", "A3", "B1", "B2", "C1", "D1"
  title: string;
  category: "upstream" | "customer" | "contractor" | "standard";
  party: string;
  effectiveDate: string;
  expiryDate: string;
  status: "ACTIVE" | "SUPERSEDED" | "AMENDED" | "EXPIRED";
  valueAnnual?: number;
  clausesCount: number;
  conflictsCount: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: "incorporates" | "amends" | "addendum_of" | "depends_on" | "conflicts_with";
  severity?: Severity;
  label?: string;
  differingClauses?: {
    sourceClauseId: string;
    targetClauseId: string;
    description: string;
    diffWords: { text: string; status: "removed" | "added" | "unchanged" }[];
  };
}

export interface ConflictFinding {
  id: string;
  title: string;
  severity: Severity;
  sourceDoc: string;
  targetDoc: string;
  sourceClauseId: string;
  targetClauseId: string;
  financialExposure: number;
  likelihood: number; // 0-100
  attackPath: string;
  description: string;
  lokiArgument: string;
  heimdallVerification: "VERIFIED" | "REFUTED" | "PARTIAL";
  heimdallNotes: string;
  tyrRuling: "UPHELD" | "DISMISSED" | "MODIFIED";
  tyrRationale: string;
  recommendedAction: string;
  clarifications?: {
    agentFrom: AgentName;
    agentTo: AgentName;
    round: number;
    question: string;
    answer: string;
    confidenceDelta: [number, number]; // e.g. [0.55, 0.91]
  }[];
}

export interface AlertItem {
  id: string;
  severity: Severity;
  title: string;
  contractId: string;
  clauseId?: string;
  dueDate: string;
  countdownDays: number;
  source: "Deadline" | "Event" | "Finding";
  description: string;
  acknowledged: boolean;
  snoozed: boolean;
  suppressed?: boolean;
  suppressionReason?: string;
}

export interface DraftedNotice {
  id: string;
  type: "renewal" | "termination" | "breach_notice" | "amendment" | "escalation";
  title: string;
  recipientName: string;
  recipientEmail: string;
  recipientAddress: string;
  targetContract: string;
  sendByDeadline: string;
  needsApproval: boolean;
  status: "DRAFT" | "APPROVED" | "REJECTED";
  confidenceScore: number;
  signatoryValid: boolean;
  signatoryName: string;
  noticeAddressValid: boolean;
  letterBody: string;
  footnotes: {
    id: number;
    clauseId: string;
    text: string;
    quote: string;
  }[];
}

export interface CheckpointSnapshot {
  id: "CP1" | "CP2" | "CP3";
  date: string;
  label: string;
  totalExposure: number;
  netUncoveredGap: number;
  insuranceCoverage: number;
  openFindingsCount: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  awaitingApprovalCount: number;
  avgConfidence: number;
  nextDeadlineDays: number;
  nextDeadlineLabel: string;
  activeEvents: string[];
  simulatedAlertDelta?: {
    alertsCount: number;
    exposureDelta: number;
  };
}

export interface GanttContractSwimlane {
  contractId: string;
  contractTitle: string;
  startDate: string;
  endDate: string;
  renewalWindow: { start: string; end: string };
  noticeDeadline: string;
  paymentEvents: { date: string; amount: number; status: "PAID" | "MISSED" | "UPCOMING" }[];
  holidayMarkers: { date: string; name: string }[];
}

export interface HeatmapCell {
  row: string;
  col: string;
  value: number; // 0-100 severity/exposure
  findingIds: string[];
}
