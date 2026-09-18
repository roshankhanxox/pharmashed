import { useState } from "react";
import { useStore } from "../../data/store";
import { LoadingView } from "../../components/shell/StateViews";
import { loadFhirBundle } from "../../data/loaders";

export function FhirTab() {
  const fhirIndex = useStore((s) => s.fhirIndex);
  const [selected, setSelected] = useState<string | null>(null);
  const [bundle, setBundle] = useState<object | null>(null);
  const [loading, setLoading] = useState(false);

  if (!fhirIndex) return <LoadingView />;

  const { resource_counts, bundles } = fhirIndex;

  async function selectBundle(name: string, path: string) {
    setSelected(name);
    setLoading(true);
    try {
      const data = await loadFhirBundle(path);
      setBundle(data as object);
    } catch {
      setBundle({ error: "Failed to load bundle" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full min-h-0" style={{ background: "#0c0a09", color: "#f5f4f2" }}>
      {/* Left: resource list */}
      <aside
        className="w-64 shrink-0 p-4 overflow-y-auto flex flex-col gap-5"
        style={{ borderRight: "1px solid #292524", background: "#0c0a09" }}
      >
        <div>
          <div
            className="text-[10px] font-semibold uppercase mb-2"
            style={{ color: "#6b6460", letterSpacing: "0.10em", fontFamily: "ui-monospace, monospace" }}
          >
            Resource counts
          </div>
          <dl className="text-xs space-y-1">
            {Object.entries(resource_counts).map(([type, count]) => (
              <div key={type} className="flex justify-between">
                <dt style={{ color: "#a6a09b" }}>{type}</dt>
                <dd style={{ color: "#f5f4f2", fontFamily: "ui-monospace, monospace" }}>{count}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div>
          <div
            className="text-[10px] font-semibold uppercase mb-2"
            style={{ color: "#6b6460", letterSpacing: "0.10em", fontFamily: "ui-monospace, monospace" }}
          >
            Bundles
          </div>
          <div className="flex flex-col gap-1">
            {bundles.map((b) => (
              <button
                key={b.name}
                onClick={() => selectBundle(b.name, b.path)}
                className="text-left px-2 py-2 text-xs rounded-lg transition-colors"
                style={{
                  background: selected === b.name ? "#1a1917" : "transparent",
                  border: `1px solid ${selected === b.name ? "#292524" : "transparent"}`,
                  color: selected === b.name ? "#7c75ff" : "#a6a09b",
                  fontFamily: "ui-monospace, monospace",
                }}
              >
                {b.name}
                <span className="ml-1.5 text-xs" style={{ color: "#6b6460" }}>({b.count})</span>
              </button>
            ))}
          </div>
        </div>

        <ValidationBadge fhirIndex={{ validation: fhirIndex.validation }} />
      </aside>

      {/* Right: explainer + JSON viewer */}
      <div className="flex-1 min-w-0 overflow-y-auto p-6 flex flex-col gap-6" style={{ background: "#0c0a09" }}>

        {/* FHIR explainer — what does this solve? */}
        <div className="rounded-xl p-5" style={{ background: "#1a1917", border: "1px solid #292524" }}>
          <div
            className="text-[10px] font-semibold uppercase mb-3"
            style={{ color: "#6b6460", letterSpacing: "0.10em", fontFamily: "ui-monospace, monospace" }}
          >
            What FHIR solves here
          </div>
          <h2 className="text-base font-semibold mb-3" style={{ color: "#f5f4f2" }}>
            Environmental predictions, interoperable with health records
          </h2>
          <p className="text-sm leading-relaxed mb-4" style={{ color: "#a6a09b" }}>
            FHIR (Fast Healthcare Interoperability Resources) is the HL7 standard for exchanging health data. The <strong style={{ color: "#f5f4f2" }}>OneAquaHealth Implementation Guide</strong> extends it to cover environmental health observations — air quality, water chemistry, pharmaceutical concentrations — in the same format as patient lab results.
          </p>
          <div className="grid gap-3 sm:grid-cols-3 mb-4">
            {[
              { icon: "⇄", title: "Interoperability", body: "A water authority and a hospital can query the same FHIR server. Environmental predictions and patient prescriptions share one standard." },
              { icon: "≠", title: "Model vs lab — distinguished", body: "category: model-prediction separates PharmaShed outputs from real lab results. Both can live in the same server, filterable by a single query parameter." },
              { icon: "⊕", title: "Co-hosted with OAH data", body: "PharmaShed bundles sit alongside the OneAquaHealth IG's own Benevento example resources — demonstrating the consortium vision of one FHIR server for the whole One Health ecosystem." },
            ].map((item) => (
              <div key={item.title} className="rounded-lg p-4" style={{ background: "#242220", border: "1px solid #292524" }}>
                <div className="text-lg mb-2" style={{ color: "#7c75ff", fontFamily: "ui-monospace, monospace" }}>{item.icon}</div>
                <div className="text-xs font-semibold mb-1" style={{ color: "#f5f4f2" }}>{item.title}</div>
                <div className="text-xs leading-relaxed" style={{ color: "#79716b" }}>{item.body}</div>
              </div>
            ))}
          </div>
          <p className="text-xs leading-relaxed" style={{ color: "#6b6460" }}>
            Each PharmaShed prediction becomes an <code className="px-1 rounded" style={{ background: "#242220", color: "#a6a09b", fontFamily: "ui-monospace, monospace" }}>Observation</code> resource with the <code className="px-1 rounded" style={{ background: "#242220", color: "#a6a09b", fontFamily: "ui-monospace, monospace" }}>observation-with-component-oah</code> profile, components for PEC p05/p50/p95, RQ p50, priority score, and LOD share — and a <code className="px-1 rounded" style={{ background: "#242220", color: "#a6a09b", fontFamily: "ui-monospace, monospace" }}>meta.tag: illustrative-parameter</code> that drops the moment real values replace illustrative ones.
          </p>
        </div>

        {/* Lab vs model panel */}
        <div className="rounded-xl p-5" style={{ background: "#1a1917", border: "1px solid #292524" }}>
          <h2 className="text-sm font-medium mb-3" style={{ color: "#f5f4f2" }}>Lab vs model queries</h2>
          <div className="flex gap-4 flex-wrap">
            <QueryBox
              label="Lab results"
              query={'Observation?category=laboratory&_count=20'}
              count={resource_counts["Observation"] ?? "?"}
            />
            <QueryBox
              label="Model predictions"
              query={'Observation?category=model-prediction&_count=20'}
              count={resource_counts["Observation"] ?? "?"}
            />
          </div>
          <p className="text-xs mt-3" style={{ color: "#6b6460" }}>
            A server query distinguishes model output from lab results via category{" "}
            <code className="px-1 rounded" style={{ background: "#242220", color: "#a6a09b", fontFamily: "ui-monospace, monospace" }}>model-prediction</code>.
          </p>
        </div>

        {/* JSON tree */}
        {loading && <LoadingView label="Loading bundle…" />}
        {!loading && bundle && (
          <div
            className="rounded-xl p-4"
            style={{ background: "#1a1917", border: "1px solid #292524" }}
          >
            <h2 className="text-sm font-medium mb-3" style={{ color: "#f5f4f2" }}>
              {selected}
            </h2>
            <div className="text-xs" style={{ fontFamily: "ui-monospace, monospace" }}>
              <JsonTree value={bundle} depth={0} />
            </div>
          </div>
        )}
        {!loading && !bundle && (
          <p className="text-xs" style={{ color: "#6b6460" }}>Select a bundle from the list to inspect its raw FHIR JSON.</p>
        )}
      </div>
    </div>
  );
}

function ValidationBadge({ fhirIndex }: { fhirIndex: { validation?: { errors?: number; status?: string; ci_log_url?: string | null } } }) {
  const errors = fhirIndex.validation?.errors ?? 0;
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs"
      style={{
        background: errors === 0 ? "#0d1f0d" : "#1f1800",
        border: `1px solid ${errors === 0 ? "#166534" : "#78350f"}`,
        color: errors === 0 ? "#4ade80" : "#fbbf24",
        fontFamily: "ui-monospace, monospace",
      }}
    >
      {errors === 0 ? (
        <span>✓ Validates against OneAquaHealth IG</span>
      ) : (
        <span>⚠ {errors} validation error{errors !== 1 ? "s" : ""}</span>
      )}
    </div>
  );
}

function QueryBox({ label, query, count }: { label: string; query: string; count: number | string }) {
  return (
    <div className="flex-1 min-w-0">
      <div className="text-xs text-neutral-400 mb-1">{label}</div>
      <code className="block bg-neutral-100 dark:bg-neutral-800 rounded p-2 text-[10px] break-all text-neutral-700 dark:text-neutral-300">
        {query}
      </code>
      <div className="text-xs text-neutral-400 mt-1">n = {count}</div>
    </div>
  );
}

const HIGHLIGHTED_KEYS = new Set(["category", "method", "derivedFrom", "component", "meta"]);

function JsonTree({ value, depth }: { value: unknown; depth: number }) {
  const [collapsed, setCollapsed] = useState(depth > 2);

  if (value === null) return <span className="text-neutral-400">null</span>;
  if (typeof value !== "object") {
    return (
      <span className={typeof value === "string" ? "text-green-700 dark:text-green-400" : "text-blue-700 dark:text-blue-400"}>
        {JSON.stringify(value)}
      </span>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-neutral-400">[]</span>;
    return (
      <span>
        <button onClick={() => setCollapsed((v) => !v)} className="text-neutral-400 hover:text-neutral-700 mr-1">
          {collapsed ? "▶" : "▼"}
        </button>
        {collapsed ? (
          <span className="text-neutral-400">[{value.length} items]</span>
        ) : (
          <ul className="ml-4 border-l border-neutral-200 dark:border-neutral-700 pl-2">
            {value.slice(0, 20).map((item, i) => (
              <li key={i}>
                <span className="text-neutral-400">{i}: </span>
                <JsonTree value={item} depth={depth + 1} />
              </li>
            ))}
            {value.length > 20 && <li className="text-neutral-400 text-xs">…{value.length - 20} more</li>}
          </ul>
        )}
      </span>
    );
  }

  const entries = Object.entries(value as Record<string, unknown>);
  if (entries.length === 0) return <span className="text-neutral-400">{"{}"}</span>;

  return (
    <span>
      <button onClick={() => setCollapsed((v) => !v)} className="text-neutral-400 hover:text-neutral-700 mr-1">
        {collapsed ? "▶" : "▼"}
      </button>
      {collapsed ? (
        <span className="text-neutral-400">{"{…}"}</span>
      ) : (
        <ul className="ml-4 border-l border-neutral-200 dark:border-neutral-700 pl-2">
          {entries.map(([k, v]) => (
            <li key={k}>
              <span className={`text-xs font-mono ${HIGHLIGHTED_KEYS.has(k) ? "text-purple-700 dark:text-purple-300 font-semibold" : "text-neutral-600 dark:text-neutral-400"}`}>
                {k}:{" "}
              </span>
              <JsonTree value={v} depth={depth + 1} />
            </li>
          ))}
        </ul>
      )}
    </span>
  );
}
