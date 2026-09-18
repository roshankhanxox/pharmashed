import { useState } from "react";
import { useStore } from "../../data/store";
import { LoadingView } from "../../components/shell/StateViews";
import { ModelDiagram } from "../../components/charts/ModelDiagram";
import { InfoButton } from "../../components/provenance/InfoButton";

const ABLATION_LABELS = ["Population only", "+ Consumption", "+ Untreated pathway (full)"];

export function MethodologyTab() {
  const methodology = useStore((s) => s.methodology);
  const [ablationIdx, setAblationIdx] = useState(2);

  if (!methodology) return <LoadingView />;

  const { stages, priors_table, identifiability_text, ablations } = methodology;

  const variantOrder = ["pop_only", "full", "full"] as const;
  const variant = variantOrder[ablationIdx] ?? "full";
  const ablationPerCity = ablations?.per_city?.filter((a) => a.variant === variant) ?? [];

  return (
    <div className="overflow-y-auto p-6 flex flex-col gap-8 max-w-4xl mx-auto">

      {/* Intro */}
      <div>
        <h1 className="text-base font-semibold mb-1">Model methodology</h1>
        <p className="text-sm text-neutral-500 leading-relaxed max-w-2xl">
          PharmaShed estimates pharmaceutical concentrations at urban stream sites using a Monte Carlo mass-balance model. The core innovation is the <strong>untreated discharge pathway</strong> (λ): drug loads reaching streams directly via sewer leakage, misconnections, and overflow events — absent from ePiE and GREAT-ER, which only model treatment-plant outfalls.
        </p>
      </div>

      {/* Model diagram */}
      <section>
        <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
          Model pipeline
        </h2>
        <ModelDiagram stages={stages} />
      </section>

      {/* Priors table */}
      <section>
        <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
          Priors
        </h2>
        <div className="overflow-x-auto">
          <table className="text-xs w-full">
            <thead>
              <tr className="text-neutral-400 border-b border-neutral-200">
                <th className="text-left py-1.5 pr-3">Parameter</th>
                <th className="text-left py-1.5 pr-3">Distribution</th>
                <th className="text-left py-1.5 pr-3">Range</th>
                <th className="text-left py-1.5 pr-3">Unit</th>
                <th className="text-left py-1.5">Status</th>
              </tr>
            </thead>
            <tbody>
              {priors_table?.map((row: PriorRow) => (
                <tr key={row.param} className="border-b border-neutral-100 dark:border-neutral-800">
                  <td className="py-1.5 pr-3 font-mono">{row.param}</td>
                  <td className="py-1.5 pr-3">{row.distribution ?? "—"}</td>
                  <td className="py-1.5 pr-3">{row.range ?? "—"}</td>
                  <td className="py-1.5 pr-3 text-neutral-400">{row.unit ?? ""}</td>
                  <td className="py-1.5">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                      row.status === "sourced"
                        ? "bg-green-100 text-green-800"
                        : row.status === "assumption"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-neutral-100 text-neutral-600"
                    }`}>
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
      {identifiability_text && (
        <section>
          <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-2">
            Identifiability
          </h2>
          <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg p-4 text-sm text-amber-900 dark:text-amber-100">
            {identifiability_text}
          </div>
        </section>
      )}

      {/* Ablation toggle */}
      {ablations && (
        <section>
          <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Ablation
          </h2>
          <div className="flex gap-0.5 mb-4">
            {ABLATION_LABELS.map((label, i) => (
              <button
                key={i}
                onClick={() => setAblationIdx(i)}
                className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                  ablationIdx === i
                    ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                    : "border-neutral-200 text-neutral-500 hover:border-blue-300"
                }`}
              >
                {label}
              </button>
            ))}
            <div className="ml-2 px-2 py-1 text-xs rounded border border-dashed border-neutral-300 text-neutral-400">
              WWTP-only (ePiE-like): predicts 0 for these streams
            </div>
          </div>
          {ablationPerCity.length > 0 && (
            <div className="flex flex-wrap gap-6">
              {ablationPerCity.map((cityData) => (
                <div key={cityData.city} className="text-xs">
                  <div className="font-medium text-neutral-500 mb-1">{cityData.city}</div>
                  <div className="flex flex-col gap-0.5">
                    {cityData.ranking.map((siteId, i) => (
                      <div key={siteId} className="flex gap-2">
                        <span className="text-neutral-400 w-4 text-right">{i + 1}.</span>
                        <span>{siteId}</span>
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
