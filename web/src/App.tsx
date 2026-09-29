import { useEffect, useState } from "react";
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
import { FloatingAsk } from "./components/shell/FloatingAsk";
import { LoadingView, InvalidView } from "./components/shell/StateViews";

import { HomeTab } from "./tabs/Home";
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

  // Page transition: fade the current tab out, then swap and fade the new one in.
  const [shownTab, setShownTab] = useState(activeTab);
  const leaving = activeTab !== shownTab;
  useEffect(() => {
    if (!leaving) return;
    const swap = setTimeout(() => setShownTab(activeTab), 150);
    return () => clearTimeout(swap);
  }, [activeTab, leaving]);

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
    <div className="h-svh flex flex-col overflow-hidden" style={{ background: "var(--c-canvas)", color: "var(--c-text)" }}>
      {isDev && <DevBanner />}
      <TopTabs />

      <main className={`flex-1 min-h-0 overflow-hidden ${leaving ? "page-out" : "page-in"}`} key={shownTab}>
        {shownTab === "home" && <HomeTab />}
        {shownTab === "explore" && <ExploreTab />}
        {shownTab === "scenarios" && <ScenariosTab />}
        {shownTab === "consistency" && <ConsistencyTab />}
        {shownTab === "methodology" && <MethodologyTab />}
        {shownTab === "fhir" && <FhirTab />}
      </main>

      <FooterStrip />
      <ProvenanceDrawer />
      <FloatingAsk />
      <AssistantDrawer />
    </div>
  );
}

export default App;
