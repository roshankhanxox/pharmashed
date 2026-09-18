import { useMemo, type ReactNode } from "react";
import { useStore } from "../../data/store";
import { applyScenario } from "../../data/scenario";
import { BandChart, type BandRow } from "../../components/charts/BandChart";
import { EmptyView, LoadingView } from "../../components/shell/StateViews";
import { Term } from "../../components/glossary/Term";

const C = {
  canvas:  "#0c0a09",
  surface: "#1a1917",
  raised:  "#242220",
  border:  "#292524",
  text:    "#f5f4f2",
  muted:   "#a6a09b",
  faint:   "#6b6460",
  indigo:  "#7c75ff",
} as const;

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
      <span className="text-xs" style={{ color: C.muted }}>
        {label}: <strong style={{ color: C.text }}>{value.toFixed(2)}×</strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-indigo-500"
        style={{ accentColor: C.indigo }}
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
    <div className="h-full flex items-center justify-center" style={{ background: C.canvas }}>
      <div className="text-center max-w-sm px-6">
        <div className="text-4xl mb-4">🗺</div>
        <h2 className="text-base font-semibold mb-2" style={{ color: C.text }}>Select a site first</h2>
        <p className="text-sm mb-5 leading-relaxed" style={{ color: C.faint }}>
          Go to the Explore tab, click any site marker on the map, then come back here to run what-if scenarios on that site.
        </p>
        <button
          onClick={() => useStore.getState().setActiveTab("explore")}
          className="px-5 py-2.5 text-sm font-medium rounded-xl transition-colors"
          style={{ background: C.indigo, color: "#fff" }}
        >
          Go to Explore →
        </button>
      </div>
    </div>
  );

  if (selectedDrug === "all") return (
    <div className="h-full flex items-center justify-center" style={{ background: C.canvas }}>
      <div className="text-center max-w-sm px-6">
        <div className="text-4xl mb-4">💊</div>
        <h2 className="text-base font-semibold mb-2" style={{ color: C.text }}>Select a specific drug</h2>
        <p className="text-sm mb-5 leading-relaxed" style={{ color: C.faint }}>
          Scenarios need a single drug to recompute scores over. In the Explore tab, select one of the six drugs from the drug filter, then return here.
        </p>
        <button
          onClick={() => useStore.getState().setActiveTab("explore")}
          className="px-5 py-2.5 text-sm font-medium rounded-xl transition-colors"
          style={{ background: C.indigo, color: "#fff" }}
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
    <div className="flex h-full min-h-0" style={{ background: C.canvas }}>
      {/* Controls sidebar */}
      <aside
        className="w-72 shrink-0 p-4 flex flex-col gap-5 overflow-y-auto scrollbar-none"
        style={{ borderRight: `1px solid ${C.border}`, background: C.canvas }}
      >
        {/* Presets */}
        <div>
          <div
            className="text-[10px] font-semibold uppercase mb-3"
            style={{ color: C.faint, letterSpacing: "0.10em", fontFamily: "ui-monospace, monospace" }}
          >
            Scenario presets
          </div>
          <div className="flex flex-col gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => setMultipliers(p.m)}
                className="text-left p-3 rounded-lg transition-all"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = C.indigo;
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = C.border;
                }}
              >
                <div className="text-xs font-medium" style={{ color: C.text }}>{p.label}</div>
                <div className="text-[11px] mt-0.5" style={{ color: C.faint }}>{p.desc}</div>
              </button>
            ))}
            {/* Riparian card */}
            <div
              className="p-3 rounded-lg"
              style={{ background: C.surface, border: `1px dashed ${C.border}` }}
            >
              <div className="text-xs font-medium" style={{ color: C.muted }}>Riparian restoration</div>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded inline-block mt-1"
                style={{ background: "#1c1400", color: "#fbbf24", border: "1px solid #78350f", fontFamily: "ui-monospace, monospace" }}
              >
                Illustrative
              </span>
              <div className="text-[11px] mt-1" style={{ color: C.faint }}>
                Assumes additional in-stream removal — set C multiplier below.
              </div>
            </div>
          </div>
        </div>

        {/* Fine controls */}
        <div className="flex flex-col gap-3">
          <div
            className="text-[10px] font-semibold uppercase"
            style={{ color: C.faint, letterSpacing: "0.10em", fontFamily: "ui-monospace, monospace" }}
          >
            Fine controls
          </div>
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
            className="text-xs text-left underline"
            style={{ color: C.faint }}
          >
            Reset to baseline
          </button>
        </div>

        <p className="text-[11px] leading-relaxed" style={{ color: C.faint }}>
          The model constrains λ/Q jointly — these controls show how much each assumption carries.
        </p>
      </aside>

      {/* Before / After panel */}
      <div className="flex-1 min-w-0 p-6 overflow-y-auto flex flex-col gap-6" style={{ background: C.canvas }}>
        <div>
          <div
            className="text-[10px] font-semibold uppercase mb-1"
            style={{ color: C.faint, letterSpacing: "0.10em", fontFamily: "ui-monospace, monospace" }}
          >
            Scenario explorer
          </div>
          <h2 className="text-base font-semibold" style={{ color: C.text }}>
            {selectedSiteId} — {selectedDrug}
          </h2>
        </div>

        {baseline && scenario && (
          <div
            className="rounded-xl p-5 flex gap-6 flex-wrap items-center"
            style={{ background: C.surface, border: `1px solid ${C.border}` }}
          >
            <div className="flex-1 min-w-36">
              <div
                className="text-[10px] font-semibold uppercase mb-1"
                style={{ color: C.faint, letterSpacing: "0.08em", fontFamily: "ui-monospace, monospace" }}
              >
                Baseline score
              </div>
              <div className="text-3xl font-bold" style={{ color: C.text, fontFamily: "ui-monospace, monospace" }}>
                {baseline.score.toFixed(3)}
              </div>
              <div className="text-xs mt-1" style={{ color: C.faint }}>
                draws with <Term term="RQ">RQ</Term> &gt; 1
              </div>
            </div>

            <div className="text-2xl" style={{ color: C.border }}>→</div>

            <div className="flex-1 min-w-36">
              <div
                className="text-[10px] font-semibold uppercase mb-1"
                style={{ color: C.faint, letterSpacing: "0.08em", fontFamily: "ui-monospace, monospace" }}
              >
                Scenario score
              </div>
              <div
                className="text-3xl font-bold"
                style={{
                  color: scenario.score > baseline.score ? "#f87171" : "#4ade80",
                  fontFamily: "ui-monospace, monospace",
                }}
              >
                {scenario.score.toFixed(3)}
              </div>
              <div className="text-xs mt-1" style={{ color: C.faint }}>
                Δ {(scenario.score - baseline.score) >= 0 ? "+" : ""}
                {(scenario.score - baseline.score).toFixed(3)}
              </div>
            </div>
          </div>
        )}

        {baseRow && scenario && (
          <div>
            <div
              className="text-[10px] font-semibold uppercase mb-2"
              style={{ color: C.faint, letterSpacing: "0.08em", fontFamily: "ui-monospace, monospace" }}
            >
              Predicted <Term term="PEC">PEC</Term> ranges — recomputed over {scenario.n} stored draws
            </div>
            <BandChart rows={[baseRow]} />
          </div>
        )}

        <p className="text-xs leading-relaxed" style={{ color: C.faint }}>
          Scores recomputed live over 1,000 stored simulation draws under stated priors. Score is the share of draws with RQ &gt; 1 — it is not a probability.
        </p>
      </div>
    </div>
  );
}
