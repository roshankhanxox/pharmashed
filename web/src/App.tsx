import { useEffect } from "react";
import { useStore } from "./data/store";
import {
  loadResults,
  loadSites,
  loadDrawsIndex,
  loadDrawsBin,
  loadProvenance,
  loadChecks,
  loadMethodology,
  loadFhirIndex,
} from "./data/loaders";
import { createDrawsView } from "./data/draws";

import { TopTabs } from "./components/shell/TopTabs";
import { FooterStrip } from "./components/shell/FooterStrip";
import { DevBanner } from "./components/shell/DevBanner";
import { ProvenanceDrawer } from "./components/provenance/ProvenanceDrawer";
import { AssistantDrawer } from "./assistant/AssistantDrawer";
import { LoadingView, InvalidView } from "./components/shell/StateViews";

import { ExploreTab } from "./tabs/Explore";
import { ScenariosTab } from "./tabs/Scenarios";
import { ConsistencyTab } from "./tabs/Consistency";
import { MethodologyTab } from "./tabs/Methodology";
import { FhirTab } from "./tabs/Fhir";

function App() {
  const activeTab = useStore((s) => s.activeTab);
  const dataLoading = useStore((s) => s.dataLoading);
  const dataError = useStore((s) => s.dataError);
  const results = useStore((s) => s.results);

  const {
    setResults, setSites, setDrawsIndex, setDrawsView,
    setProvenance, setChecks, setMethodology, setFhirIndex,
    setDataError, setDataLoading,
  } = useStore();

  useEffect(() => {
    async function load() {
      try {
        const [r, s, idx, bin, prov, chk, meth, fhir] = await Promise.all([
          loadResults(),
          loadSites(),
          loadDrawsIndex(),
          loadDrawsBin(),
          loadProvenance(),
          loadChecks(),
          loadMethodology(),
          loadFhirIndex(),
        ]);
        setResults(r);
        setSites(s);
        setDrawsIndex(idx);
        setDrawsView(createDrawsView(idx, bin));
        setProvenance(prov);
        setChecks(chk);
        setMethodology(meth);
        setFhirIndex(fhir);
      } catch (e) {
        setDataError((e as Error).message);
      } finally {
        setDataLoading(false);
      }
    }
    void load();
  }, []);

  if (dataLoading) {
    return (
      <div className="min-h-svh flex items-center justify-center">
        <LoadingView label="Loading PharmaShed data…" />
      </div>
    );
  }

  if (dataError) {
    return (
      <div className="min-h-svh flex items-center justify-center">
        <InvalidView message={`Failed to load data: ${dataError}`} />
      </div>
    );
  }

  const isDev = results?.meta.dev_placeholders ?? false;

  return (
    <div className="min-h-svh flex flex-col bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100">
      {isDev && <DevBanner />}
      <TopTabs />

      <main className="flex-1 min-h-0 overflow-hidden" style={{ height: "calc(100vh - 96px)" }}>
        {activeTab === "explore" && <ExploreTab />}
        {activeTab === "scenarios" && <ScenariosTab />}
        {activeTab === "consistency" && <ConsistencyTab />}
        {activeTab === "methodology" && <MethodologyTab />}
        {activeTab === "fhir" && <FhirTab />}
      </main>

      <FooterStrip />
      <ProvenanceDrawer />
      <AssistantDrawer />
    </div>
  );
}

export default App;
