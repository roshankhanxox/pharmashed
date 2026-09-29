import { create } from "zustand";
import type {
  ConsistencyChecks,
  DrawsIndex,
  FHIRIndex,
  Methodology,
  Provenance,
  Results,
  Sites,
} from "../types/contracts";
import type { DrawsView } from "./draws";

export type Tab = "home" | "explore" | "scenarios" | "consistency" | "methodology" | "fhir";

/** Who the interface is written for. Citizen = plain language and simpler tabs; expert = full technical view. */
export type Audience = "citizen" | "expert";

/** Tabs that only exist in expert view. */
export const EXPERT_ONLY_TABS: readonly Tab[] = ["consistency", "methodology", "fhir"];

const AUDIENCE_KEY = "ps-audience";
const DEFAULT_AUDIENCE: Audience = "citizen";

/** Reads the saved audience; falls back to the default if storage is unavailable. */
function loadAudience(): Audience {
  try {
    const v = localStorage.getItem(AUDIENCE_KEY);
    return v === "expert" || v === "citizen" ? v : DEFAULT_AUDIENCE;
  } catch {
    return DEFAULT_AUDIENCE;
  }
}

export interface ScenarioMultipliers {
  lambda: number;
  Q: number;
  C: number;
}

export interface AppStore {
  // loaded data
  results: Results | null;
  sites: Sites | null;
  drawsIndex: DrawsIndex | null;
  drawsView: DrawsView | null;
  provenance: Provenance | null;
  checks: ConsistencyChecks | null;
  methodology: Methodology | null;
  fhirIndex: FHIRIndex | null;
  dataError: string | null;
  dataLoading: boolean;

  // navigation
  audience: Audience;
  activeTab: Tab;
  selectedCity: string | null;
  selectedSiteId: string | null;
  selectedDrug: string;
  expandedDrug: string | null;

  // scenario
  scenarioMultipliers: ScenarioMultipliers;

  // drawers
  assistantOpen: boolean;
  provenanceKey: string | null;

  // actions
  setResults: (r: Results) => void;
  setSites: (s: Sites) => void;
  setDrawsIndex: (i: DrawsIndex) => void;
  setDrawsView: (v: DrawsView) => void;
  setProvenance: (p: Provenance) => void;
  setChecks: (c: ConsistencyChecks) => void;
  setMethodology: (m: Methodology) => void;
  setFhirIndex: (f: FHIRIndex) => void;
  setDataError: (e: string | null) => void;
  setDataLoading: (v: boolean) => void;

  setAudience: (a: Audience) => void;
  setActiveTab: (t: Tab) => void;
  setSelectedCity: (c: string | null) => void;
  setSelectedSiteId: (id: string | null) => void;
  setSelectedDrug: (d: string) => void;
  setExpandedDrug: (d: string | null) => void;

  setScenarioMultipliers: (m: Partial<ScenarioMultipliers>) => void;
  resetScenario: () => void;

  openAssistant: () => void;
  closeAssistant: () => void;
  openProvenance: (key: string) => void;
  closeProvenance: () => void;
}

const DEFAULT_MULTIPLIERS: ScenarioMultipliers = { lambda: 1, Q: 1, C: 1 };

export const useStore = create<AppStore>((set, get) => ({
  results: null,
  sites: null,
  drawsIndex: null,
  drawsView: null,
  provenance: null,
  checks: null,
  methodology: null,
  fhirIndex: null,
  dataError: null,
  dataLoading: true,

  audience: loadAudience(),
  activeTab: "home",
  selectedCity: null,
  selectedSiteId: null,
  selectedDrug: "citalopram",
  expandedDrug: null,

  scenarioMultipliers: { ...DEFAULT_MULTIPLIERS },

  assistantOpen: false,
  provenanceKey: null,

  setResults: (r) => set({ results: r }),
  setSites: (s) => set({ sites: s }),
  setDrawsIndex: (i) => set({ drawsIndex: i }),
  setDrawsView: (v) => set({ drawsView: v }),
  setProvenance: (p) => set({ provenance: p }),
  setChecks: (c) => set({ checks: c }),
  setMethodology: (m) => set({ methodology: m }),
  setFhirIndex: (f) => set({ fhirIndex: f }),
  setDataError: (e) => set({ dataError: e }),
  setDataLoading: (v) => set({ dataLoading: v }),

  setAudience: (a) => {
    try {
      localStorage.setItem(AUDIENCE_KEY, a);
    } catch {
      /* storage unavailable — the choice still applies for this visit */
    }
    // A citizen has no expert-only tabs, so leave one if we are on it.
    const leaveTab = a === "citizen" && EXPERT_ONLY_TABS.includes(get().activeTab);
    set({ audience: a, ...(leaveTab ? { activeTab: "home" as Tab } : {}) });
  },
  setActiveTab: (t) => set({ activeTab: t }),
  setSelectedCity: (c) => set({ selectedCity: c }),
  setSelectedSiteId: (id) => set({ selectedSiteId: id }),
  setSelectedDrug: (d) => set({ selectedDrug: d }),
  setExpandedDrug: (d) => set({ expandedDrug: d }),

  setScenarioMultipliers: (m) =>
    set((s) => ({ scenarioMultipliers: { ...s.scenarioMultipliers, ...m } })),
  resetScenario: () => set({ scenarioMultipliers: { ...DEFAULT_MULTIPLIERS } }),

  openAssistant: () => set({ assistantOpen: true }),
  closeAssistant: () => set({ assistantOpen: false }),
  openProvenance: (key) => set({ provenanceKey: key }),
  closeProvenance: () => set({ provenanceKey: null }),
}));
