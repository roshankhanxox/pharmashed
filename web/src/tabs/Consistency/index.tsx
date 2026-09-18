import { useStore } from "../../data/store";
import { LoadingView } from "../../components/shell/StateViews";
import { DotOnBand } from "../../components/charts/DotOnBand";
import { Scatter, type ScatterPoint } from "../../components/charts/Scatter";

export function ConsistencyTab() {
  const checks = useStore((s) => s.checks);
  if (!checks) return <LoadingView />;

  const { meta, circularity_statement, checks: rawItems } = checks;
  const items = rawItems as unknown as CheckItem[];

  return (
    <div className="overflow-y-auto p-6 flex flex-col gap-6 max-w-3xl mx-auto" style={{ background: "#0c0a09", color: "#f5f4f2" }}>

      {/* D35 reframing header */}
      <div>
        <h1 className="text-base font-semibold mb-1">How validation runs once parameters are sourced</h1>
        <p className="text-sm leading-relaxed" style={{ color: "#a6a09b" }}>
          These five checks compare PharmaShed's predicted outputs against <strong>Rodrigues et al. 2025</strong> independently collected field data. Predictions were frozen before comparison to prevent post-hoc tuning. While parameters remain illustrative (D33), results carry an "illustrative inputs" label — they are not evidence of model accuracy, but demonstrate that the validation pipeline works correctly and is ready to run the moment real parameters are in place.
        </p>
      </div>

      {/* Freeze provenance */}
      <div className="flex items-center gap-3 rounded-lg px-4 py-3 text-xs" style={{ background: "#1a1917", border: "1px solid #292524", color: "#a6a09b" }}>
        <span className="text-lg">🔒</span>
        <span>
          Predictions frozen at tag{" "}
          <code className="px-1.5 py-0.5 rounded" style={{ background: "#242220", color: "#7c75ff", fontFamily: "ui-monospace, monospace" }}>{meta.frozen_tag}</code>
          {" · "}sha256{" "}
          <code className="px-1.5 py-0.5 rounded" style={{ background: "#242220", color: "#a6a09b", fontFamily: "ui-monospace, monospace" }}>{meta.frozen_sha256.slice(0, 12)}…</code>
        </span>
      </div>

      {/* Circularity callout */}
      <div className="rounded-lg p-4 text-sm" style={{ background: "#0d1624", border: "1px solid #1e3a5f", color: "#93c5fd" }}>
        <strong className="block mb-1" style={{ color: "#bfdbfe" }}>On circularity</strong>
        {circularity_statement}
      </div>

      {/* Checks */}
      {items.map((check) => (
        <CheckCard key={check.id} check={check} />
      ))}

      {/* Illustrative caveat */}
      <div className="rounded-lg px-4 py-3 text-xs" style={{ background: "#1c1400", border: "1px solid #78350f", color: "#fbbf24" }}>
        ⚗ All checks run on predictions derived from <strong>illustrative parameters</strong> (D33). Pass/fail results are demonstrations of the pipeline, not evidence of model accuracy against real data.
      </div>
    </div>
  );
}

interface CheckData {
  points?: ScatterPoint[];
  rho?: number;
  n?: number;
  min_p5?: number;
  max_p95?: number;
  observed_max?: number;
  observed?: string[];
  predicted?: string[];
  tau?: number;
  rows?: Array<{ site_id: string; rank_change: number }>;
}

interface CheckItem {
  id: string;
  status: "pass" | "fail" | "unavailable";
  reason: string | null;
  data: CheckData;
}

function CheckCard({ check }: { check: CheckItem }) {
  const statusStyle =
    check.status === "pass"
      ? { background: "#052e16", color: "#4ade80", border: "1px solid #166534" }
      : check.status === "fail"
      ? { background: "#450a0a", color: "#f87171", border: "1px solid #7f1d1d" }
      : { background: "#1a1917", color: "#a6a09b", border: "1px solid #292524" };

  const TITLES: Record<string, string> = {
    C1: "C1 — LOD share vs detection frequency",
    C2: "C2 — Observed city ranking",
    C3: "C3 — Predicted city ranking",
    C4: "C4 — Observed max within predicted range",
    C5: "C5 — Rank stability across ablation steps",
  };

  const EXPLANATIONS: Record<string, string> = {
    C1: "For each drug, the model predicts what share of draws produce a concentration below the detection limit (LOD). This check asks: does that predicted share match how often the drug was actually detected in the Rodrigues 2025 field data? A high Spearman ρ means the model correctly identifies which drugs are hardest to detect.",
    C2: "The five cities were ranked by observed total pharmaceutical load in Rodrigues 2025 (TLS > GNT > BNV > CBR ≈ OSL). This check verifies that the observed ranking used for comparison is consistent with the published data.",
    C3: "The model produces a predicted city ranking by summing scores. This check asks: does the model's predicted city order agree with the observed ranking? A high Kendall τ means the model correctly identifies the highest-load cities without having been told the answers.",
    C4: "For each drug, the model predicts a range of concentrations (p5–p95). This check asks: does the maximum observed concentration in the field data fall within the range the model predicted — and not more than 10× above it? A pass means the model's uncertainty bands are appropriately calibrated.",
    C5: "The model has three ablation variants: population-only, full (with untreated pathway), and a WWTP-only baseline that mimics ePiE/GREAT-ER. This check verifies that site priority rankings stay stable when switching between the full and population-only variants, isolating how much the untreated pathway adds.",
  };

  return (
    <div className="rounded-xl p-4 flex flex-col gap-3" style={{ background: "#1a1917", border: "1px solid #292524" }}>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium" style={{ color: "#f5f4f2" }}>{TITLES[check.id] ?? check.id}</h3>
        <span
          className="text-xs font-medium px-2 py-0.5 rounded"
          style={{ ...statusStyle, fontFamily: "ui-monospace, monospace", fontSize: "10px", letterSpacing: "0.04em" }}
        >
          {check.status}
        </span>
      </div>

      {EXPLANATIONS[check.id] && (
        <p className="text-xs leading-relaxed pl-3" style={{ color: "#79716b", borderLeft: "2px solid #292524" }}>
          {EXPLANATIONS[check.id]}
        </p>
      )}

      {check.reason && (
        <p className="text-xs font-medium" style={{ color: check.status === "fail" ? "#f87171" : "#a6a09b" }}>
          Result: {check.reason}
        </p>
      )}

      {/* C4: DotOnBand */}
      {check.id === "C4" && check.data.min_p5 != null && check.data.max_p95 != null && check.data.observed_max != null && (
        <DotOnBand
          minP5={check.data.min_p5}
          maxP95={check.data.max_p95}
          observedMax={check.data.observed_max}
        />
      )}

      {/* C1: Scatter */}
      {check.id === "C1" && check.data.points && (
        <Scatter
          points={check.data.points}
          rho={check.data.rho}
          n={check.data.n}
          xLabel="Predicted LOD share"
          yLabel="Observed det. freq."
        />
      )}

      {/* C2/C3: rank lists */}
      {(check.id === "C2" || check.id === "C3") && check.data.observed && (
        <div className="flex gap-6 text-xs">
          <div>
            <div className="font-medium text-neutral-500 mb-1">Observed</div>
            {check.data.observed.map((s, i) => (
              <div key={i}>{i + 1}. {s}</div>
            ))}
          </div>
          <div>
            <div className="font-medium text-neutral-500 mb-1">Predicted</div>
            {check.data.predicted?.map((s, i) => (
              <div key={i}>{i + 1}. {s}</div>
            ))}
          </div>
          {check.data.tau != null && (
            <div className="self-end text-neutral-400">
              τ = {check.data.tau.toFixed(3)}
            </div>
          )}
        </div>
      )}

      {/* C5: rank change table */}
      {check.id === "C5" && check.data.rows && (
        <table className="text-xs w-full">
          <thead>
            <tr className="text-neutral-400">
              <th className="text-left py-1">Site</th>
              <th className="text-right py-1">Rank change</th>
            </tr>
          </thead>
          <tbody>
            {check.data.rows.map((r) => (
              <tr key={r.site_id}>
                <td className="py-0.5">{r.site_id}</td>
                <td className={`text-right py-0.5 ${r.rank_change !== 0 ? "text-amber-600" : "text-green-600"}`}>
                  {r.rank_change > 0 ? `+${r.rank_change}` : r.rank_change}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
