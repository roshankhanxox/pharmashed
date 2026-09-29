import { useState } from "react";
import { useStore } from "../../data/store";
import { LoadingView } from "../../components/shell/StateViews";
import { ModelDiagram } from "../../components/charts/ModelDiagram";
import { InfoButton } from "../../components/provenance/InfoButton";

const ABLATION_LABELS = ["WWTP-only (ePiE baseline)", "Population only", "Full model"];

const ABLATION_DESCRIPTIONS = [
  "Mimics ePiE and GREAT-ER: drug loads routed only via wastewater treatment plant outfalls. Every site in this dataset has w = 0 (no WWTP on the stream), so this model predicts PEC = 0 everywhere — rankings are arbitrary. This is the blind spot PharmaShed addresses.",
  "Uses only the population within a 500 m buffer of each site to estimate drug load. No national consumption data, no λ. Shows what population density alone tells you — it rank-orders cities but misses within-city variation driven by infrastructure quality.",
  "The full PharmaShed model: population × national consumption rates × untreated leakage fraction λ ∈ (0.002, 0.15). This is what the Explore map shows. Compare with Population-only to see how much the untreated pathway (λ) adds.",
];

export function MethodologyTab() {
  const methodology = useStore((s) => s.methodology);
  const [ablationIdx, setAblationIdx] = useState(2); // default: Full model

  if (!methodology) return <LoadingView />;

  const { stages, priors_table, identifiability_text, ablations } = methodology;

  const variantOrder = ["wwtp_only", "pop_only", "full"] as const;
  const variant = variantOrder[ablationIdx] ?? "full";
  const ablationPerCity = ablations?.per_city?.filter((a) => a.variant === variant) ?? [];

  return (
    <div className="h-full overflow-y-auto p-6 flex flex-col gap-8 max-w-4xl mx-auto" style={{ background: "var(--c-canvas)", color: "var(--c-text)" }}>

      {/* Intro */}
      <div>
        <h1 className="text-base font-semibold mb-1">Model methodology</h1>
        <p className="text-sm leading-relaxed max-w-2xl" style={{ color: "var(--c-muted)" }}>
          PharmaShed estimates pharmaceutical concentrations at urban stream sites using a Monte Carlo mass-balance model. The core innovation is the <strong>untreated discharge pathway</strong> (λ): drug loads reaching streams directly via sewer leakage, misconnections, and overflow events — absent from ePiE and GREAT-ER, which only model treatment-plant outfalls.
        </p>
      </div>

      {/* Model diagram */}
      <section>
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-3"
          style={{ color: "var(--c-faint)" }}
        >
          Model pipeline
        </h2>
        <ModelDiagram stages={stages} />
      </section>

      {/* Priors table */}
      <section>
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
                  <td className="py-2 px-3" style={{ color: "var(--c-indigo)" }}>{row.param}</td>
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
      </section>

      {/* Identifiability */}
      <section>
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
      </section>

      {/* Ablation toggle */}
      {ablations && (
        <section>
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
                  background: ablationIdx === i ? "rgba(124,117,255,0.15)" : "var(--c-surface)",
                  border: `1px solid ${ablationIdx === i ? "var(--c-indigo)" : "var(--c-border)"}`,
                  color: ablationIdx === i ? "var(--c-indigo)" : "var(--c-muted)",
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
        </section>
      )}
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
