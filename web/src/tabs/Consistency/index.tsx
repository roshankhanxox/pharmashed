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
    <div className="overflow-y-auto p-6 flex flex-col gap-6 max-w-3xl mx-auto">
      {/* Circularity callout */}
      <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4 text-sm text-blue-900 dark:text-blue-100">
        <strong className="block mb-1">On circularity</strong>
        {circularity_statement}
      </div>

      {/* Checks */}
      {items.map((check) => (
        <CheckCard key={check.id} check={check} />
      ))}

      {/* Footer */}
      <div className="text-xs text-neutral-400">
        Predictions committed before comparison — tag{" "}
        <code className="bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{meta.frozen_tag}</code>,
        sha256 <code className="bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{meta.frozen_sha256.slice(0, 12)}…</code>
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
  const statusColor =
    check.status === "pass"
      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
      : check.status === "fail"
      ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100"
      : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400";

  const TITLES: Record<string, string> = {
    C1: "C1 — Predicted LOD share vs observed detection frequency",
    C2: "C2 — Observed city ranking correlation",
    C3: "C3 — Predicted city ranking correlation",
    C4: "C4 — Observed max within predicted range",
    C5: "C5 — Rank stability across ablation steps",
  };

  return (
    <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium">{TITLES[check.id] ?? check.id}</h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${statusColor}`}>
          {check.status}
        </span>
      </div>

      {check.reason && (
        <p className={`text-xs ${check.status === "fail" ? "text-red-600" : "text-neutral-500"}`}>
          {check.reason}
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
