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

/** City id of a site id ("TLS-01" -> "TLS"). */
export function cityOfSite(siteId: string): string {
  return siteId.split("-")[0];
}

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

/** The site (and optionally drug) the assistant has been asked about, sent to the API as context. */
export interface AssistantContext {
  siteId: string;
  drug: string | null;
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
  assistantContext: AssistantContext | null;
  /** A question typed outside the drawer (Home ask bar); the drawer sends it once and clears it. */
  assistantPendingQuestion: string | null;
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
  /** Opens the assistant already focused on a site (and optionally a drug). */
  openAssistantFor: (siteId: string, drug?: string | null) => void;
  clearAssistantContext: () => void;
  /** Opens the assistant and asks a question straight away. */
  openAssistantWith: (question: string) => void;
  clearPendingQuestion: () => void;
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
  assistantContext: null,
  assistantPendingQuestion: null,
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
  // City and site selection stay consistent: switching to another city drops a site that belongs to a
  // different city (the inspector then shows that city's top sites), and picking a site moves the
  // city filter to the site's city. Site ids look like "TLS-01": the prefix is the city id.
  setSelectedCity: (c) =>
    set((s) =>
      c && s.selectedSiteId && cityOfSite(s.selectedSiteId) !== c
        ? { selectedCity: c, selectedSiteId: null, expandedDrug: null }
        : { selectedCity: c },
    ),
  setSelectedSiteId: (id) =>
    set(id ? { selectedSiteId: id, selectedCity: cityOfSite(id) } : { selectedSiteId: null }),
  setSelectedDrug: (d) => set({ selectedDrug: d }),
  setExpandedDrug: (d) => set({ expandedDrug: d }),

  setScenarioMultipliers: (m) =>
    set((s) => ({ scenarioMultipliers: { ...s.scenarioMultipliers, ...m } })),
  resetScenario: () => set({ scenarioMultipliers: { ...DEFAULT_MULTIPLIERS } }),

  openAssistant: () => set({ assistantOpen: true }),
  openAssistantFor: (siteId, drug = null) =>
    set({ assistantOpen: true, assistantContext: { siteId, drug } }),
  clearAssistantContext: () => set({ assistantContext: null }),
  openAssistantWith: (question) => set({ assistantOpen: true, assistantPendingQuestion: question }),
  clearPendingQuestion: () => set({ assistantPendingQuestion: null }),
  closeAssistant: () => set({ assistantOpen: false }),
  openProvenance: (key) => set({ provenanceKey: key }),
  closeProvenance: () => set({ provenanceKey: null }),
}));
