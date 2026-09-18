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
    <div className="flex h-full min-h-0">
      {/* Left: resource list */}
      <aside className="w-56 shrink-0 border-r border-neutral-200 dark:border-neutral-800 p-4 overflow-y-auto flex flex-col gap-4">
        <div>
          <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-wide mb-2">
            Resource counts
          </h2>
          <dl className="text-xs space-y-1">
            {Object.entries(resource_counts).map(([type, count]) => (
              <div key={type} className="flex justify-between">
                <dt className="text-neutral-600 dark:text-neutral-400">{type}</dt>
                <dd className="font-mono text-neutral-800 dark:text-neutral-200">{count}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div>
          <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-wide mb-2">
            Bundles
          </h2>
          <div className="flex flex-col gap-1">
            {bundles.map((b) => (
              <button
                key={b.name}
                onClick={() => selectBundle(b.name, b.path)}
                className={`text-left px-2 py-1.5 text-xs rounded-md transition-colors ${
                  selected === b.name
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200"
                    : "hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-600"
                }`}
              >
                {b.name}
                <span className="ml-1 text-neutral-400">({b.count})</span>
              </button>
            ))}
          </div>
        </div>

        <ValidationBadge fhirIndex={{ validation: fhirIndex.validation }} />
      </aside>

      {/* Right: JSON viewer + lab/model panel */}
      <div className="flex-1 min-w-0 overflow-y-auto p-4 flex flex-col gap-4">
        {/* Lab vs model panel */}
        <div className="bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
          <h2 className="text-sm font-medium mb-3">Lab vs model queries</h2>
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
          <p className="text-xs text-neutral-500 mt-3">
            A server query can distinguish model output from lab results via category{" "}
            <code className="bg-neutral-100 dark:bg-neutral-800 px-1 rounded">model-prediction</code>.
          </p>
        </div>

        {/* JSON tree */}
        {loading && <LoadingView label="Loading bundle…" />}
        {!loading && bundle && (
          <div>
            <h2 className="text-sm font-medium mb-2">
              {selected} bundle
            </h2>
            <JsonTree value={bundle} depth={0} />
          </div>
        )}
        {!loading && !bundle && (
          <p className="text-sm text-neutral-400">Select a bundle from the list.</p>
        )}
      </div>
    </div>
  );
}

function ValidationBadge({ fhirIndex }: { fhirIndex: { validation?: { errors?: number; status?: string; ci_log_url?: string | null } } }) {
  const errors = fhirIndex.validation?.errors ?? 0;
  return (
    <div className={`rounded-md px-3 py-2 text-xs ${errors === 0 ? "bg-green-50 text-green-700 border border-green-200" : "bg-amber-50 text-amber-700 border border-amber-200"}`}>
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
