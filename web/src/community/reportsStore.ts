/** Report state: the loaded reports, the map layer toggle, and the filing flow (pick a spot, answer, send). */
import { create } from "zustand";
import { ApiError } from "./api";
import { useCommunity } from "./store";
import { fetchReports, flagReport, postReport, type Report, type ReportInput } from "./reports";

export interface Spot {
  lat: number;
  lon: number;
}

interface ReportsState {
  reports: Report[];
  /** The "citizen reports (unverified)" map layer. */
  layerOn: boolean;
  /** True while the person is choosing a spot by clicking the map. */
  picking: boolean;
  dialogOpen: boolean;
  spot: Spot | null;
  busy: boolean;
  error: string | null;
  /** Set after a successful send, so the map can show it and the dialog can thank the person. */
  justSent: Report | null;
  /** The report being flagged, and whether the flag was sent. */
  flagging: Report | null;
  flagDone: boolean;

  load: () => Promise<void>;
  setLayerOn: (on: boolean) => void;
  /** Open the dialog, optionally at a known spot (e.g. a site). */
  startReport: (spot?: Spot | null) => void;
  startPicking: () => void;
  pickSpot: (spot: Spot) => void;
  cancel: () => void;
  startFlag: (report: Report) => void;
  closeFlag: () => void;
  sendFlag: (reason: string) => Promise<boolean>;
  submit: (input: Omit<ReportInput, "lat" | "lon">) => Promise<boolean>;
}

export const useReports = create<ReportsState>((set, get) => ({
  reports: [],
  layerOn: true,
  picking: false,
  dialogOpen: false,
  spot: null,
  busy: false,
  error: null,
  justSent: null,
  flagging: null,
  flagDone: false,

  load: async () => {
    try {
      set({ reports: await fetchReports(useCommunity.getState().signedIn) });
    } catch {
      // Reports are an extra layer: if they cannot load, the rest of the app is unaffected.
    }
  },
  setLayerOn: (on) => set({ layerOn: on }),
  startReport: (spot = null) => set({ dialogOpen: true, picking: false, spot, error: null, justSent: null }),
  startPicking: () => set({ dialogOpen: false, picking: true }),
  pickSpot: (spot) => set({ spot, picking: false, dialogOpen: true, error: null }),
  startFlag: (report) => set({ flagging: report, flagDone: false, error: null }),
  closeFlag: () => set({ flagging: null, flagDone: false, error: null }),
  sendFlag: async (reason) => {
    const { flagging } = get();
    if (!flagging) return false;
    set({ busy: true, error: null });
    try {
      const result = await flagReport(flagging.id, reason);
      // A report that three people flagged is held: take it off the map straight away.
      set((s) => ({ busy: false, flagDone: true, reports: result.held ? s.reports.filter((r) => r.id !== flagging.id) : s.reports }));
      return true;
    } catch (e) {
      set({ busy: false, error: e instanceof Error ? e.message : "Could not send the flag." });
      return false;
    }
  },
  cancel: () => set({ dialogOpen: false, picking: false, error: null, justSent: null }),

  submit: async (input) => {
    const { spot } = get();
    if (!spot) {
      set({ error: "Choose where you are first." });
      return false;
    }
    set({ busy: true, error: null });
    try {
      const report = await postReport({ ...input, ...spot });
      set((s) => ({ busy: false, justSent: report, reports: [report, ...s.reports], layerOn: true }));
      return true;
    } catch (e) {
      const message = e instanceof ApiError || e instanceof Error ? e.message : "Could not send the report.";
      set({ busy: false, error: message });
      return false;
    }
  },
}));
