import { useState } from "react";
import { useStore } from "../../data/store";
import { LoadingView } from "../../components/shell/StateViews";
import { ModelDiagram } from "../../components/charts/ModelDiagram";
import { Reveal } from "../../components/shell/Reveal";
import { useSmoothScroll } from "../../hooks/useSmoothScroll";
import { InfoButton } from "../../components/provenance/InfoButton";


/** The model as implemented in engine/src/pharmashed/model.py (A4). Keep in step with that file. */
const EQUATIONS: { label: string; formula: string }[] = [
  { label: "1. Consumed near the site", formula: "L = P · C · DDD / 1000   (g/day)" },
  { label: "2. Excreted unchanged", formula: "E = L · fe   (g/day)" },
  { label: "3. Reaching the stream", formula: "M = E · ( λ + w · (1 − λ) · (1 − R) )   (g/day)" },
  { label: "4. Concentration (PEC)", formula: "PEC = M / (Q · 86 400 · 1 000) · e^(−k·τ) · 10⁹   (ng/L)" },
  { label: "5. Risk quotient", formula: "RQ = PEC / PNEC" },
  { label: "6. Sampling-priority score", formula: "score = share of draws with RQ > 1" },
];

const SYMBOLS: { sym: string; text: string }[] = [
  { sym: "P", text: "people within 500 m of the site (GHS-POP)" },
  { sym: "C", text: "consumption, DDD per 1 000 people per day (country value × a 0.8–1.25 multiplier)" },
  { sym: "DDD", text: "defined daily dose of the drug, in grams" },
  { sym: "fe", text: "fraction excreted unchanged" },
  { sym: "λ", text: "untreated leakage fraction (log-uniform 0.002–0.15)" },
  { sym: "w, R", text: "treatment-plant flag (0 here) and its removal efficiency" },
  { sym: "Q", text: "stream flow in m³/s, drawn per size class (S, M, L)" },
  { sym: "k, τ", text: "in-stream loss rate per hour and travel time (0.5–12 h)" },
  { sym: "PNEC", text: "predicted no-effect concentration, ng/L" },
];

const ABLATION_LABELS = ["WWTP-only (ePiE baseline)", "Population only", "Full model"];

const ABLATION_DESCRIPTIONS = [
  "Mimics ePiE and GREAT-ER: drug loads routed only via wastewater treatment plant outfalls. Every site in this dataset has w = 0 (no WWTP on the stream), so this model predicts PEC = 0 everywhere — rankings are arbitrary. This is the blind spot PharmaShed addresses.",
  "Uses only the population within a 500 m buffer of each site to estimate drug load. No national consumption data, no λ. Shows what population density alone tells you — it rank-orders cities but misses within-city variation driven by infrastructure quality.",
  "The full PharmaShed model: population × national consumption rates × untreated leakage fraction λ ∈ (0.002, 0.15). This is what the Explore map shows. Compare with Population-only to see how much the untreated pathway (λ) adds.",
];

export function MethodologyTab() {
  const scrollRef = useSmoothScroll();
  const methodology = useStore((s) => s.methodology);
  const [ablationIdx, setAblationIdx] = useState(2); // default: Full model

  if (!methodology) return <LoadingView />;

  const { stages, priors_table, identifiability_text, ablations } = methodology;

  const variantOrder = ["wwtp_only", "pop_only", "full"] as const;
  const variant = variantOrder[ablationIdx] ?? "full";
  const ablationPerCity = ablations?.per_city?.filter((a) => a.variant === variant) ?? [];

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto" style={{ background: "var(--c-canvas)", color: "var(--c-text)" }}>
      <div className="p-6 flex flex-col gap-8 max-w-4xl mx-auto">

      {/* Intro */}
      <div>
        <h1 className="text-base font-semibold mb-1">Model methodology</h1>
        <p className="text-sm leading-relaxed max-w-2xl" style={{ color: "var(--c-muted)" }}>
          PharmaShed estimates pharmaceutical concentrations at urban stream sites using a Monte Carlo mass-balance model. The core innovation is the <strong>untreated discharge pathway</strong> (λ): drug loads reaching streams directly via sewer leakage, misconnections, and overflow events — absent from ePiE and GREAT-ER, which only model treatment-plant outfalls.
        </p>
      </div>

      {/* The equations: exactly what the engine computes (engine/src/pharmashed/model.py) */}
      <Reveal><section>
        <h2 className="text-sm font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--c-faint)" }}>
          The equations
        </h2>
        <div className="rounded-xl p-5 flex flex-col gap-4" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
          <ol className="flex flex-col gap-3 text-sm" style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
            {EQUATIONS.map((e) => (
              <li key={e.label} className="flex flex-col sm:flex-row sm:items-baseline gap-x-4">
                <span className="sm:w-72 shrink-0" style={{ color: "var(--c-faint)", fontFamily: "inherit" }}>{e.label}</span>
                <span style={{ color: "var(--c-text)" }}>{e.formula}</span>
              </li>
            ))}
          </ol>
          <p className="text-sm leading-relaxed" style={{ color: "var(--c-muted)" }}>
            Every site in this dataset has no treatment plant on its stream (<strong>w = 0</strong>), so the load reaching the stream reduces to
            <strong> M = E · λ</strong>: only the untreated pathway. A model that counts treatment-plant outfalls alone (ePiE, GREAT-ER style) predicts zero here.
          </p>
          <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-1.5 text-sm" style={{ color: "var(--c-muted)" }}>
            {SYMBOLS.map((x) => (
              <div key={x.sym} className="flex gap-2">
                <dt className="w-10 shrink-0 font-semibold" style={{ color: "var(--c-accent)" }}>{x.sym}</dt>
                <dd>{x.text}</dd>
              </div>
            ))}
          </dl>
          <p className="text-sm leading-relaxed" style={{ color: "var(--c-muted)" }}>
            λ, Q, τ and the consumption multiplier are drawn from the priors below in each of the 1,000 Monte Carlo draws; the other symbols are fixed per drug or per site.
            The <strong>sampling-priority score</strong> is the share of draws with RQ &gt; 1. It is <strong>not</strong> a probability of harm: it is an index under stated priors.
            Tiers: high ≥ 0.5, medium ≥ 0.1, low below. All drug parameters are currently illustrative placeholders.
          </p>
        </div>
      </section></Reveal>

      {/* Model diagram */}
      <Reveal><section>
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-3"
          style={{ color: "var(--c-faint)" }}
        >
          Model pipeline
        </h2>
        <ModelDiagram stages={stages} />
      </section></Reveal>

      {/* Priors table */}
      <Reveal><section>
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-3"
          style={{ color: "var(--c-faint)" }}
        >
          Priors
        </h2>
        <div
          className="overflow-x-auto rounded-xl"
          style={{ border: "1px solid var(--c-border)" }}
        >
          <table className="text-xs w-full">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--c-border)", background: "var(--c-surface)" }}>
                {["Parameter", "Distribution", "Range", "Unit", "Status"].map((h) => (
                  <th
                    key={h}
                    className="text-left py-2.5 px-3 font-semibold"
                    style={{ color: "var(--c-faint)", letterSpacing: "0.04em", fontSize: "12px" }}
                  >
                    {h.toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {priors_table?.map((row: PriorRow) => (
                <tr key={row.param} style={{ borderBottom: "1px solid var(--c-border-subtle)" }}>
                  <td className="py-2 px-3" style={{ color: "var(--c-accent)" }}>{row.param}</td>
                  <td className="py-2 px-3" style={{ color: "var(--c-muted)" }}>{row.distribution ?? "—"}</td>
                  <td className="py-2 px-3" style={{ color: "var(--c-muted)" }}>{row.range ?? "—"}</td>
                  <td className="py-2 px-3" style={{ color: "var(--c-faint)" }}>{row.unit ?? ""}</td>
                  <td className="py-2 px-3">
                    <span
                      className="px-1.5 py-0.5 rounded text-xs"
                      style={
                        row.status === "sourced"
                          ? { background: "var(--c-ok-bg)", color: "var(--c-ok-text)" }
                          : row.status === "assumption"
                          ? { background: "var(--c-warn-bg)", color: "var(--c-warn-text)" }
                          : { background: "var(--c-surface)", color: "var(--c-faint)" }
                      }
                    >
                      {row.status}
                    </span>
                    {row.provenance_key && (
                      <InfoButton provKey={row.provenance_key} />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section></Reveal>

      {/* Identifiability */}
      <Reveal><section>
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-3"
          style={{ color: "var(--c-faint)" }}
        >
          Identifiability
        </h2>
        <div
          className="rounded-xl p-5 text-sm leading-relaxed"
          style={{ background: "var(--c-warn-bg)", border: "1px solid var(--c-warn-border)", color: "var(--c-warn-text)" }}
        >
          <div className="font-semibold mb-2" style={{ color: "var(--c-warn-strong)" }}>λ and Q are not jointly identifiable from a single PEC measurement</div>
          <p style={{ color: "var(--c-warn-soft)" }}>
            {identifiability_text || (
              <>
                The leakage fraction λ and river flow Q appear as a ratio in the PEC equation: PEC ∝ λ / Q.
                A high observed concentration could equally be explained by high leakage <em>or</em> low flow.
                A single grab sample cannot separate the two. The priors on λ and Q are stated independently — their joint posterior is not recoverable without repeated sampling under varying flow conditions.
                This is a known limitation and a design choice: PharmaShed uses the prior uncertainty explicitly (via Monte Carlo) rather than pretending to estimate λ and Q separately.
              </>
            )}
          </p>
          <p className="text-xs mt-3" style={{ color: "var(--c-warn-dim)" }}>
            Implication: the score reflects uncertainty under prior assumptions, not a posterior estimate. This is intentional and disclosed — see D08 in CONTEXT.md.
          </p>
        </div>
      </section></Reveal>

      {/* Ablation toggle */}
      {ablations && (
        <Reveal><section>
          <h2
            className="text-sm font-semibold uppercase tracking-wide mb-2"
            style={{ color: "var(--c-faint)" }}
          >
            Ablation — how much does each component add?
          </h2>
          <p className="text-xs mb-4 leading-relaxed" style={{ color: "var(--c-muted2)" }}>
            The ablation compares how site priority rankings change as model components are added one at a time. A large rank shift shows that the component carries meaningful information.
          </p>

          {/* WWTP-only explanation banner */}
          <div
            className="rounded-xl p-4 mb-4 text-xs leading-relaxed"
            style={{ background: "var(--c-danger-bg)", border: "1px solid var(--c-danger-border)", color: "var(--c-danger-text)" }}
          >
            <div className="font-semibold mb-1" style={{ color: "var(--c-danger-strong)" }}>
              WWTP-only baseline (ePiE / GREAT-ER equivalent) → predicts PEC = 0 for every site here
            </div>
            WWTP = Wastewater Treatment Plant. Standard models (ePiE, GREAT-ER) route all drug load through WWTP outfalls.
            Every site in this dataset has w = 0 — no WWTP on the stream — so the WWTP-only model predicts zero pharmaceutical concentration at all 105 sites.
            This is the blind spot PharmaShed addresses.
          </div>

          {/* Step buttons */}
          <div className="flex flex-wrap gap-2 mb-4">
            {ABLATION_LABELS.map((label, i) => (
              <button
                key={i}
                onClick={() => setAblationIdx(i)}
                className="px-3 py-1.5 text-xs rounded-lg transition-all"
                style={{
                  background: ablationIdx === i ? "var(--c-accent-tint)" : "var(--c-surface)",
                  border: `1px solid ${ablationIdx === i ? "var(--c-accent)" : "var(--c-border)"}`,
                  color: ablationIdx === i ? "var(--c-accent)" : "var(--c-muted)",
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Description of selected step */}
          {ABLATION_DESCRIPTIONS[ablationIdx] && (
            <div
              className="rounded-lg px-4 py-3 text-xs leading-relaxed mb-4"
              style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)", color: "var(--c-muted)" }}
            >
              {ABLATION_DESCRIPTIONS[ablationIdx]}
            </div>
          )}

          {variant === "wwtp_only" && (
            <div
              className="rounded-lg px-4 py-3 text-xs"
              style={{ background: "var(--c-danger-bg)", border: "1px solid var(--c-danger-border)", color: "var(--c-danger-text)" }}
            >
              No rankings to show — all sites score 0 under the WWTP-only model.
              Switch to <strong style={{ color: "var(--c-danger-strong)" }}>Full model</strong> to see how the untreated pathway changes everything.
            </div>
          )}

          {variant !== "wwtp_only" && ablationPerCity.length > 0 && (
            <div className="flex flex-wrap gap-6">
              {ablationPerCity.map((cityData) => (
                <div key={cityData.city} className="text-xs">
                  <div
                    className="font-semibold mb-2"
                    style={{ color: "var(--c-text)" }}
                  >
                    {cityData.city}
                  </div>
                  <div className="flex flex-col gap-1">
                    {cityData.ranking.map((siteId, i) => (
                      <div key={siteId} className="flex gap-2">
                        <span className="w-4 text-right shrink-0" style={{ color: "var(--c-faint)" }}>{i + 1}.</span>
                        <span style={{ color: "var(--c-muted)" }}>{siteId}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section></Reveal>
      )}
      </div>
    </div>
  );
}

interface PriorRow {
  param: string;
  distribution?: string;
  range?: string;
  unit?: string;
  status?: string;
  provenance_key?: string;
}
