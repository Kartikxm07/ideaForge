import { create } from "zustand";
import {
  MOCK_SNAPSHOTS,
  MOCK_CONTRACTS,
  MOCK_CLAUSES,
  MOCK_GRAPH_EDGES,
  MOCK_CONFLICTS,
  MOCK_ALERTS,
  MOCK_ACTIONS,
  MOCK_SWIMLANES,
  MOCK_HEATMAP,
} from "@/mock/odinData";
import {
  CheckpointSnapshot,
  ContractNode,
  Clause,
  GraphEdge,
  ConflictFinding,
  AlertItem,
  DraftedNotice,
  GanttContractSwimlane,
  HeatmapCell,
} from "@/types/odin";

export type WarRoomTab = "plan" | "graph" | "exposure" | "timeline" | "debate" | "actions" | "trace";

interface OdinState {
  // Clock state
  currentDate: string;
  activeCheckpoint: "CP1" | "CP2" | "CP3";
  isPlaying: boolean;
  playbackSpeed: 1 | 4 | 16;
  
  // Navigation
  activeTab: WarRoomTab;
  setActiveTab: (tab: WarRoomTab) => void;

  // Global Modals / Drawers
  evidenceClauseId: string | null;
  openEvidence: (clauseId: string) => void;
  closeEvidence: () => void;

  diffConflictId: string | null;
  openDiff: (conflictId: string) => void;
  closeDiff: () => void;

  isAddEventOpen: boolean;
  openAddEvent: () => void;
  closeAddEvent: () => void;

  // View Controls
  exposureMode: "expected" | "worst-case";
  setExposureMode: (mode: "expected" | "worst-case") => void;

  heatmapMode: "contract-month" | "clause-month" | "contract-clause";
  setHeatmapMode: (mode: "contract-month" | "clause-month" | "contract-clause") => void;

  // Data
  contracts: ContractNode[];
  clauses: Clause[];
  edges: GraphEdge[];
  conflicts: ConflictFinding[];
  alerts: AlertItem[];
  actions: DraftedNotice[];
  swimlanes: GanttContractSwimlane[];
  heatmap: HeatmapCell[];
  currentSnapshot: CheckpointSnapshot;

  // Clock Actions
  setCheckpoint: (cp: "CP1" | "CP2" | "CP3") => void;
  setDate: (date: string) => void;
  togglePlay: () => void;
  setSpeed: (speed: 1 | 4 | 16) => void;
  stepDays: (days: number) => void;
  jumpNextDeadline: () => void;
  jumpPrevDeadline: () => void;

  // Interactive Actions
  acknowledgeAlert: (alertId: string) => void;
  snoozeAlert: (alertId: string) => void;
  approveAction: (actionId: string) => void;
  rejectAction: (actionId: string, reason?: string) => void;
  addEvent: (event: { date: string; type: string; summary: string; contractId?: string }) => void;
}

export const useOdinStore = create<OdinState>((set, get) => ({
  currentDate: "2026-11-15",
  activeCheckpoint: "CP2",
  isPlaying: false,
  playbackSpeed: 1,

  activeTab: "graph",
  setActiveTab: (tab) => set({ activeTab: tab }),

  evidenceClauseId: null,
  openEvidence: (clauseId) => set({ evidenceClauseId: clauseId }),
  closeEvidence: () => set({ evidenceClauseId: null }),

  diffConflictId: null,
  openDiff: (conflictId) => set({ diffConflictId: conflictId }),
  closeDiff: () => set({ diffConflictId: null }),

  isAddEventOpen: false,
  openAddEvent: () => set({ isAddEventOpen: true }),
  closeAddEvent: () => set({ isAddEventOpen: false }),

  exposureMode: "expected",
  setExposureMode: (mode) => set({ exposureMode: mode }),

  heatmapMode: "contract-month",
  setHeatmapMode: (mode) => set({ heatmapMode: mode }),

  contracts: MOCK_CONTRACTS,
  clauses: MOCK_CLAUSES,
  edges: MOCK_GRAPH_EDGES,
  conflicts: MOCK_CONFLICTS,
  alerts: MOCK_ALERTS,
  actions: MOCK_ACTIONS,
  swimlanes: MOCK_SWIMLANES,
  heatmap: MOCK_HEATMAP,
  currentSnapshot: MOCK_SNAPSHOTS["CP2"],

  setCheckpoint: (cp) => {
    const snapshot = MOCK_SNAPSHOTS[cp];
    set({
      activeCheckpoint: cp,
      currentDate: snapshot.date,
      currentSnapshot: snapshot,
    });
  },

  setDate: (date) => {
    set({ currentDate: date });
  },

  togglePlay: () => {
    set((state) => ({ isPlaying: !state.isPlaying }));
  },

  setSpeed: (speed) => {
    set({ playbackSpeed: speed });
  },

  stepDays: (days) => {
    const { currentDate } = get();
    const curr = new Date(currentDate);
    curr.setDate(curr.getDate() + days);
    const newDateStr = curr.toISOString().split("T")[0];
    
    // Auto align checkpoint if close
    let newCp: "CP1" | "CP2" | "CP3" = "CP1";
    if (newDateStr >= "2027-01-01") newCp = "CP3";
    else if (newDateStr >= "2026-11-01") newCp = "CP2";

    set({
      currentDate: newDateStr,
      activeCheckpoint: newCp,
      currentSnapshot: MOCK_SNAPSHOTS[newCp],
    });
  },

  jumpNextDeadline: () => {
    const { alerts, currentDate } = get();
    const futureAlerts = alerts
      .filter((a) => a.dueDate > currentDate && !a.suppressed)
      .sort((a, b) => a.dueDate.localeCompare(b.dueDate));

    if (futureAlerts.length > 0) {
      const nextDate = futureAlerts[0].dueDate;
      get().setDate(nextDate);
    }
  },

  jumpPrevDeadline: () => {
    const { alerts, currentDate } = get();
    const pastAlerts = alerts
      .filter((a) => a.dueDate < currentDate && !a.suppressed)
      .sort((a, b) => b.dueDate.localeCompare(a.dueDate));

    if (pastAlerts.length > 0) {
      const prevDate = pastAlerts[0].dueDate;
      get().setDate(prevDate);
    }
  },

  acknowledgeAlert: (alertId) => {
    set((state) => ({
      alerts: state.alerts.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a)),
    }));
  },

  snoozeAlert: (alertId) => {
    set((state) => ({
      alerts: state.alerts.map((a) => (a.id === alertId ? { ...a, snoozed: true } : a)),
    }));
  },

  approveAction: (actionId) => {
    set((state) => ({
      actions: state.actions.map((act) =>
        act.id === actionId ? { ...act, status: "APPROVED", needsApproval: false } : act
      ),
    }));
  },

  rejectAction: (actionId, reason) => {
    set((state) => ({
      actions: state.actions.map((act) =>
        act.id === actionId ? { ...act, status: "REJECTED", needsApproval: false } : act
      ),
    }));
  },

  addEvent: (event) => {
    const newAlert: AlertItem = {
      id: `ALT-NEW-${Date.now()}`,
      severity: "HIGH",
      title: event.summary,
      contractId: event.contractId || "A1",
      dueDate: event.date,
      countdownDays: 5,
      source: "Event",
      description: `Operational event ingested: ${event.summary} [Type: ${event.type}]`,
      acknowledged: false,
      snoozed: false,
    };

    set((state) => ({
      alerts: [newAlert, ...state.alerts],
      isAddEventOpen: false,
    }));
  },
}));
