export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type AgentName = "Thor" | "Norns" | "Loki" | "Heimdall" | "Tyr" | "Odin";

export type CitationStatus = "EXACT" | "FUZZY" | "NOT_FOUND";

export type EvidenceType = "SOURCED" | "INFERRED" | "FLAGGED";

export type FindingStatus = "PROMOTED" | "CONTESTED" | "DISMISSED";

export type RiskLevel = "High" | "Medium" | "Low" | "No Risk";

export type ContractStatus = "Active" | "Expiring" | "Amended" | "Pending" | "Terminated";

export interface ClauseMetadata {
  type: string;
  startDate?: string;
  initialTerm?: string;
  noticePeriod?: string;
  autoRenewal?: string;
  confidence: number;
  liabilityCap?: string;
  slaTarget?: string;
  creditTier?: string;
  governingLaw?: string;
}

export interface Clause {
  id: string; // e.g. "A2-S4.2" or "saas-c2.1"
  contractId: string;
  contractTitle: string;
  section: string;
  heading: string;
  text: string;
  highlightSnippet?: string;
  type: "uptime" | "liability" | "notice" | "termination" | "payment" | "ip" | "amendment" | "renewal" | "compliance";
  confidence: number; // 0-1
  citationStatus: CitationStatus;
  evidenceType: EvidenceType;
  status: FindingStatus;
  page?: number;
  sourceRef?: string;
  metadata?: ClauseMetadata;
  scoreBreakdown?: {
    citation: number; // 0-100
    confidence: number;
    agreement: number;
    external: number;
    composite: number;
  };
  provenance?: {
    extractedBy: AgentName;
    timestamp: string;
    docOffset?: number;
    contentHash?: string;
  };
}

export interface ContractNode {
  id: string; // e.g. "C-01", "A1", "STD", "B1"
  title: string;
  counterparty: string;
  party?: string;
  category: "upstream" | "customer" | "contractor" | "standard" | "internal";
  startDate: string;
  endDate: string;
  effectiveDate?: string;
  expiryDate?: string;
  riskLevel: RiskLevel;
  status: ContractStatus;
  valueAnnual?: number;
  clausesCount: number;
  conflictsCount: number;
  clauses?: Clause[];
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
    confidenceDelta: [number, number];
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

export interface UpcomingDeadline {
  id: string;
  month: string;
  day: string;
  title: string;
  counterparty: string;
  daysRemaining: string;
  urgency: "urgent" | "warning" | "normal";
}

export interface AgentStatusInfo {
  id: AgentName;
  name: string;
  role: string;
  status: "Active" | "Idle" | "Running" | "Completed";
  progress: number;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: string;
  contractsProcessed?: number;
  clausesExtracted?: number;
  avgConfidence?: number;
  currentTask?: {
    contractName: string;
    step: string;
    progress: number;
  };
  keyExtractions?: {
    category: string;
    count: number;
    confidence: number;
  }[];
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
}

export interface GanttContractSwimlane {
  contractId: string;
  contractTitle: string;
  startDate: string;
  endDate: string;
  milestones: {
    date: string;
    type: "payment" | "renewal" | "notice" | "penalty";
    label: string;
    amount?: number;
  }[];
}

export interface HeatmapCell {
  row: string;
  col: string;
  value: number;
  findingIds: string[];
}
