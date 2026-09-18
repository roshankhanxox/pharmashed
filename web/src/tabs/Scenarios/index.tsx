import { useMemo, type ReactNode } from "react";
import { useStore } from "../../data/store";
import { applyScenario } from "../../data/scenario";
import { BandChart, type BandRow } from "../../components/charts/BandChart";
import { EmptyView, LoadingView } from "../../components/shell/StateViews";
import { Term } from "../../components/glossary/Term";

const PRESETS = [
  { label: "Sewer repair", desc: "Targeted repair reduces untreated discharge by half.", m: { lambda: 0.5 } },
  { label: "Drought", desc: "Low river flow reduces dilution 5-fold.", m: { Q: 0.2 } },
  { label: "Leakage hotspot", desc: "Barcelona-type high-leakage case (λ × 3).", m: { lambda: 3 } },
];

function SliderField({
  label, value, min, max, step, onChange,
}: {
  label: ReactNode; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-neutral-500">
        {label}: <strong>{value.toFixed(2)}×</strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-blue-600"
      />
    </label>
  );
}

export function ScenariosTab() {
  const results = useStore((s) => s.results);
  const drawsView = useStore((s) => s.drawsView);
  const selectedSiteId = useStore((s) => s.selectedSiteId);
  const selectedDrug = useStore((s) => s.selectedDrug);
  const multipliers = useStore((s) => s.scenarioMultipliers);
  const setMultipliers = useStore((s) => s.setScenarioMultipliers);
  const resetScenario = useStore((s) => s.resetScenario);

  const siteEntry = useMemo(
    () => results?.results.find((r) => r.site_id === selectedSiteId && r.drug === selectedDrug),
    [results, selectedSiteId, selectedDrug]
  );

  const draws = useMemo(() => {
    if (!drawsView || !selectedSiteId) return null;
    return drawsView.slice(selectedSiteId, selectedDrug);
  }, [drawsView, selectedSiteId, selectedDrug]);

  const baseline = useMemo(() => {
    if (!draws || draws.length === 0) return null;
    return applyScenario(draws, { lambda: 1, Q: 1, C: 1 });
  }, [draws]);

  const scenario = useMemo(() => {
    if (!draws || draws.length === 0) return null;
    return applyScenario(draws, multipliers);
  }, [draws, multipliers]);

  if (!results) return <LoadingView />;
  if (!selectedSiteId) return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-sm px-6">
        <div className="text-4xl mb-4">🗺</div>
        <h2 className="text-base font-semibold mb-2">Select a site first</h2>
        <p className="text-sm text-neutral-500 mb-5">
          Go to the Explore tab, click any site marker on the map, then come back here to run what-if scenarios on that site.
        </p>
        <button
          onClick={() => useStore.getState().setActiveTab("explore")}
          className="px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition-colors"
        >
          Go to Explore →
        </button>
      </div>
    </div>
  );
  if (selectedDrug === "all") return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-sm px-6">
        <div className="text-4xl mb-4">💊</div>
        <h2 className="text-base font-semibold mb-2">Select a specific drug</h2>
        <p className="text-sm text-neutral-500 mb-5">
          Scenarios need a single drug to recompute scores over. In the Explore tab, select one of the six drugs from the drug row, then return here.
        </p>
        <button
          onClick={() => useStore.getState().setActiveTab("explore")}
          className="px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition-colors"
        >
          Go to Explore →
        </button>
      </div>
    </div>
  );
  if (!draws || draws.length === 0) return <EmptyView reason="No stored draws for this site/drug combination." />;

  const baseRow: BandRow | null = siteEntry
    ? {
        drug: selectedDrug,
        p5: siteEntry.pec_ng_l.p5,
        p50: siteEntry.pec_ng_l.p50,
        p95: siteEntry.pec_ng_l.p95,
        pnec: siteEntry.pnec_ng_l,
        lod: siteEntry.lod_ng_l ?? null,
        score: baseline?.score ?? siteEntry.score,
        tier: siteEntry.tier,
      }
    : null;

  return (
    <div className="flex h-full min-h-0">
      {/* Controls */}
      <aside className="w-72 shrink-0 border-r border-neutral-200 dark:border-neutral-800 p-4 flex flex-col gap-5 overflow-y-auto">
        <div>
          <h2 className="text-sm font-semibold mb-3">Scenario presets</h2>
          <div className="flex flex-col gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => setMultipliers(p.m)}
                className="text-left p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-blue-400 transition-colors"
              >
                <div className="text-sm font-medium">{p.label}</div>
                <div className="text-xs text-neutral-400 mt-0.5">{p.desc}</div>
              </button>
            ))}
            <div className="p-3 rounded-lg border border-dashed border-neutral-300 bg-neutral-50 dark:bg-neutral-900">
              <div className="text-sm font-medium text-neutral-600">Riparian restoration</div>
              <div className="text-xs text-yellow-700 bg-yellow-100 rounded px-1 py-0.5 inline-block mt-1">
                Illustrative — not part of core model
              </div>
              <div className="text-xs text-neutral-400 mt-1">
                Assumes additional in-stream removal — set C multiplier below.
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold">Fine controls</h2>
          <SliderField
            label={<><Term term="λ">λ</Term> (leakage)</>}
            value={multipliers.lambda}
            min={0.1}
            max={10}
            step={0.1}
            onChange={(v) => setMultipliers({ lambda: v })}
          />
          <SliderField
            label={<><Term term="Q">Q</Term> (flow)</>}
            value={multipliers.Q}
            min={0.1}
            max={10}
            step={0.1}
            onChange={(v) => setMultipliers({ Q: v })}
          />
          <SliderField
            label="Consumption"
            value={multipliers.C}
            min={0.5}
            max={2}
            step={0.1}
            onChange={(v) => setMultipliers({ C: v })}
          />
          <button
            onClick={resetScenario}
            className="text-xs text-neutral-400 underline text-left"
          >
            Reset to baseline
          </button>
        </div>
        <p className="text-xs text-neutral-400">
          The model constrains λ/Q jointly — these controls show how much each assumption carries.
        </p>
      </aside>

      {/* Before/after */}
      <div className="flex-1 min-w-0 p-6 overflow-y-auto flex flex-col gap-6">
        <h2 className="text-base font-semibold">
          {selectedSiteId} — {selectedDrug}
        </h2>

        {baseline && scenario && (
          <div className="flex gap-6 flex-wrap">
            <div className="flex-1 min-w-48">
              <div className="text-xs text-neutral-400 mb-1">Baseline score</div>
              <div className="text-3xl font-bold text-neutral-800 dark:text-neutral-100">
                {baseline.score.toFixed(3)}
              </div>
              <div className="text-xs text-neutral-400">
                (draws with <Term term="RQ">RQ</Term> &gt; 1)
              </div>
            </div>
            <div className="text-2xl text-neutral-300 self-center">→</div>
            <div className="flex-1 min-w-48">
              <div className="text-xs text-neutral-400 mb-1">Scenario score</div>
              <div
                className={`text-3xl font-bold ${
                  scenario.score > baseline.score ? "text-red-600" : "text-green-600"
                }`}
              >
                {scenario.score.toFixed(3)}
              </div>
              <div className="text-xs text-neutral-400">
                Δ {(scenario.score - baseline.score) >= 0 ? "+" : ""}
                {(scenario.score - baseline.score).toFixed(3)}
              </div>
            </div>
          </div>
        )}

        {baseRow && scenario && (
          <div>
            <div className="text-xs text-neutral-400 mb-2">
              Predicted <Term term="PEC">PEC</Term> ranges (recomputed over {scenario.n} stored simulation draws)
            </div>
            <BandChart rows={[baseRow]} />
          </div>
        )}

        <p className="text-xs text-neutral-400">
          Scores recomputed live over 1,000 stored simulation draws under stated priors.
        </p>
      </div>
    </div>
  );
}
