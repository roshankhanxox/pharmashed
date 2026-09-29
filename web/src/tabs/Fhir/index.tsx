import { useState } from "react";
import { useSmoothScroll } from "../../hooks/useSmoothScroll";
import { useStore } from "../../data/store";
import { LoadingView } from "../../components/shell/StateViews";
import { loadFhirBundle } from "../../data/loaders";
import { validationBadge, type ValidationInfo } from "./validation";

const OAH_BUNDLE_NAME = "oah-examples";

export function FhirTab() {
  const scrollRef = useSmoothScroll();
  const fhirIndex = useStore((s) => s.fhirIndex);
  const [selected, setSelected] = useState<string | null>(null);
  const [bundle, setBundle] = useState<object | null>(null);
  const [loading, setLoading] = useState(false);
  const [oahExpanded, setOahExpanded] = useState(false);
  const [oahBundle, setOahBundle] = useState<object | null>(null);
  const [oahLoading, setOahLoading] = useState(false);

  if (!fhirIndex) return <LoadingView />;

  const { resource_counts, bundles } = fhirIndex;
  const oahMeta = (fhirIndex as unknown as Record<string, unknown>)["oah_example_counts"] as Record<string, unknown> | undefined;
  const pharmaBundles = bundles.filter((b) => b.name !== OAH_BUNDLE_NAME);
  const oahBundleMeta = bundles.find((b) => b.name === OAH_BUNDLE_NAME);

  async function loadOahBundle() {
    if (!oahBundleMeta || oahBundle) return;
    setOahLoading(true);
    try {
      const data = await loadFhirBundle(oahBundleMeta.path);
      setOahBundle(data as object);
    } catch {
      setOahBundle({ error: "Failed to load OAH examples bundle" });
    } finally {
      setOahLoading(false);
    }
  }

  function toggleOah() {
    setOahExpanded((v) => !v);
    loadOahBundle();
  }

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
    <div className="flex h-full min-h-0" style={{ background: "var(--c-canvas)", color: "var(--c-text)" }}>
      {/* Left: resource list */}
      <aside
        className="w-64 shrink-0 p-4 overflow-y-auto flex flex-col gap-5"
        style={{ borderRight: "1px solid var(--c-border)", background: "var(--c-canvas)" }}
      >
        <div>
          <div
            className="text-xs font-semibold uppercase mb-2"
            style={{ color: "var(--c-faint)", letterSpacing: "0.06em" }}
          >
            Resource counts
          </div>
          <dl className="text-xs space-y-1">
            {Object.entries(resource_counts).map(([type, count]) => (
              <div key={type} className="flex justify-between">
                <dt style={{ color: "var(--c-muted)" }}>{type}</dt>
                <dd style={{ color: "var(--c-text)" }}>{count}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div>
          <div
            className="text-xs font-semibold uppercase mb-2"
            style={{ color: "var(--c-faint)", letterSpacing: "0.06em" }}
          >
            Bundles
          </div>
          <div className="flex flex-col gap-1">
            {pharmaBundles.map((b) => (
              <button
                key={b.name}
                onClick={() => selectBundle(b.name, b.path)}
                className="text-left px-2 py-2 text-xs rounded-lg transition-colors"
                style={{
                  background: selected === b.name ? "var(--c-surface)" : "transparent",
                  border: `1px solid ${selected === b.name ? "var(--c-border)" : "transparent"}`,
                  color: selected === b.name ? "var(--c-accent)" : "var(--c-muted)",
                }}
              >
                {b.name}
                <span className="ml-1.5 text-xs" style={{ color: "var(--c-faint)" }}>({b.count})</span>
              </button>
            ))}
          </div>
        </div>

        <ValidationBadge validation={fhirIndex.validation} />
      </aside>

      {/* Right: explainer + JSON viewer */}
      <div ref={scrollRef} className="flex-1 min-w-0 overflow-y-auto p-6 flex flex-col gap-6" style={{ background: "var(--c-canvas)" }}>

        {/* FHIR explainer — what does this solve? */}
        <div className="rounded-xl p-5" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
          <div
            className="text-xs font-semibold uppercase mb-3"
            style={{ color: "var(--c-faint)", letterSpacing: "0.06em" }}
          >
            What FHIR solves here
          </div>
          <h2 className="text-base font-semibold mb-3" style={{ color: "var(--c-text)" }}>
            Environmental predictions, interoperable with health records
          </h2>
          <p className="text-sm leading-relaxed mb-4" style={{ color: "var(--c-muted)" }}>
            FHIR (Fast Healthcare Interoperability Resources) is the HL7 standard for exchanging health data. The <strong style={{ color: "var(--c-text)" }}>OneAquaHealth Implementation Guide</strong> extends it to cover environmental health observations — air quality, water chemistry, pharmaceutical concentrations — in the same format as patient lab results.
          </p>
          <div className="grid gap-3 sm:grid-cols-3 mb-4">
            {[
              { icon: "⇄", title: "Interoperability", body: "A water authority and a hospital can query the same FHIR server. Environmental predictions and patient prescriptions share one standard." },
              { icon: "≠", title: "Model vs lab — distinguished", body: "category: model-prediction separates PharmaShed outputs from real lab results. Both can live in the same server, filterable by a single query parameter." },
              { icon: "⊕", title: "Co-hosted with OAH data", body: "PharmaShed bundles sit alongside the OneAquaHealth IG's own example resources — Benevento air quality (Benzene, NO₂) and Almyros water chemistry (aluminium dissolved) — demonstrating the consortium vision of one FHIR server for the whole One Health ecosystem. See the OAH Examples panel below." },
            ].map((item) => (
              <div key={item.title} className="rounded-lg p-4" style={{ background: "var(--c-raised)", border: "1px solid var(--c-border)" }}>
                <div className="text-lg mb-2" style={{ color: "var(--c-accent)" }}>{item.icon}</div>
                <div className="text-xs font-semibold mb-1" style={{ color: "var(--c-text)" }}>{item.title}</div>
                <div className="text-xs leading-relaxed" style={{ color: "var(--c-muted2)" }}>{item.body}</div>
              </div>
            ))}
          </div>
          <p className="text-xs leading-relaxed" style={{ color: "var(--c-faint)" }}>
            Each PharmaShed prediction becomes an <code className="px-1 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)" }}>Observation</code> resource with the <code className="px-1 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)" }}>observation-with-component-oah</code> profile, components for PEC p05/p50/p95, RQ p50, priority score, and LOD share — and a <code className="px-1 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)" }}>meta.tag: illustrative-parameter</code> that drops the moment real values replace illustrative ones.
          </p>
        </div>

        {/* Lab vs model panel */}
        <div className="rounded-xl p-5" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
          <h2 className="text-sm font-medium mb-3" style={{ color: "var(--c-text)" }}>Lab vs model queries</h2>
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
          <p className="text-xs mt-3" style={{ color: "var(--c-faint)" }}>
            A server query distinguishes model output from lab results via category{" "}
            <code className="px-1 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)" }}>model-prediction</code>.
          </p>
        </div>

        {/* JSON tree */}
        {loading && <LoadingView label="Loading bundle…" />}
        {!loading && bundle && (
          <div
            className="rounded-xl p-4"
            style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}
          >
            <h2 className="text-sm font-medium mb-3" style={{ color: "var(--c-text)" }}>
              {selected}
            </h2>
            <div className="text-xs" style={{ }}>
              <JsonTree value={bundle} depth={0} />
            </div>
          </div>
        )}
        {!loading && !bundle && (
          <p className="text-xs" style={{ color: "var(--c-faint)" }}>Select a bundle from the list to inspect its raw FHIR JSON.</p>
        )}

        {/* OAH IG Examples panel */}
        {oahBundleMeta && (
          <div className="rounded-xl" style={{ background: "var(--c-surface)", border: "1px solid var(--c-accent)" }}>
            {/* Header row — click to expand */}
            <div
              className="flex items-center justify-between px-5 py-4 cursor-pointer select-none"
              onClick={toggleOah}
            >
              <div>
                <div
                  className="text-xs font-semibold uppercase mb-1"
                  style={{ color: "var(--c-accent)", letterSpacing: "0.06em" }}
                >
                  OneAquaHealth IG · Example data
                </div>
                <div className="text-sm font-semibold" style={{ color: "var(--c-text)" }}>
                  OAH consortium resources co-hosted on this server
                </div>
                <div className="text-xs mt-0.5" style={{ color: "var(--c-muted)" }}>
                  Benevento air quality (Benzene, NO₂) · Almyros water chemistry — unmodified, credited to OAH IG (hl7-eu/oah)
                </div>
              </div>
              <div className="shrink-0 ml-4 text-xs" style={{ color: "var(--c-accent)" }}>
                {oahExpanded ? "▲ collapse" : "▼ expand"}
              </div>
            </div>

            {oahExpanded && (
              <div className="px-5 pb-5 flex flex-col gap-4" style={{ borderTop: "1px solid var(--c-border)" }}>
                {/* Resource count chips */}
                {oahMeta && (
                  <div className="flex flex-wrap gap-2 pt-4">
                    {(["Location", "Organization", "Observation"] as const).map((type) => (
                      <div
                        key={type}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs"
                        style={{ background: "var(--c-raised)", border: "1px solid var(--c-border)" }}
                      >
                        <span style={{ color: "var(--c-accent)", fontWeight: 600 }}>
                          {String(oahMeta[type] ?? 0)}
                        </span>
                        <span style={{ color: "var(--c-muted)" }}>{type}</span>
                      </div>
                    ))}
                    <div
                      className="flex items-center px-2.5 py-1 rounded-lg text-xs"
                      style={{ background: "var(--c-raised)", border: "1px solid var(--c-border)", color: "var(--c-faint)" }}
                    >
                      category: laboratory
                    </div>
                  </div>
                )}

                <p className="text-xs leading-relaxed" style={{ color: "var(--c-muted)" }}>
                  These resources use the same{" "}
                  <code className="px-1 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)" }}>ObservationWithCompOah</code>{" "}
                  profile as PharmaShed predictions. Both are distinguishable by{" "}
                  <code className="px-1 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)" }}>category</code>:
                  OAH examples use <code className="px-1 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)" }}>laboratory</code>;
                  PharmaShed uses <code className="px-1 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)" }}>model-prediction</code>.
                  A single query parameter separates them on the same server.
                </p>

                {oahLoading && <LoadingView label="Loading OAH examples…" />}
                {!oahLoading && oahBundle && (
                  <div
                    className="rounded-lg p-3 text-xs overflow-x-auto"
                    style={{ background: "var(--c-canvas)", border: "1px solid var(--c-border)" }}
                  >
                    <JsonTree value={oahBundle} depth={0} />
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ValidationBadge({ validation }: { validation?: ValidationInfo }) {
  const { tone, text } = validationBadge(validation);
  const colours = {
    ok: { bg: "var(--c-ok-bg)", border: "var(--c-ok-border)", text: "var(--c-ok-text)" },
    warn: { bg: "var(--c-warn-bg)", border: "var(--c-warn-border)", text: "var(--c-warn-text)" },
    neutral: { bg: "var(--c-raised)", border: "var(--c-border)", text: "var(--c-muted)" },
  }[tone];
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs"
      style={{ background: colours.bg, border: `1px solid ${colours.border}`, color: colours.text }}
    >
      <span>{text}</span>
    </div>
  );
}

function QueryBox({ label, query, count }: { label: string; query: string; count: number | string }) {
  return (
    <div className="flex-1 min-w-0">
      <div className="text-xs text-neutral-600 dark:text-neutral-400 mb-1">{label}</div>
      <code className="block bg-neutral-100 dark:bg-neutral-800 rounded p-2 text-xs break-all text-neutral-700 dark:text-neutral-300">
        {query}
      </code>
      <div className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">n = {count}</div>
    </div>
  );
}

const HIGHLIGHTED_KEYS = new Set(["category", "method", "derivedFrom", "component", "meta"]);

function JsonTree({ value, depth }: { value: unknown; depth: number }) {
  const [collapsed, setCollapsed] = useState(depth > 2);

  if (value === null) return <span className="text-neutral-600 dark:text-neutral-400">null</span>;
  if (typeof value !== "object") {
    return (
      <span className={typeof value === "string" ? "text-green-700 dark:text-green-400" : "text-blue-700 dark:text-blue-400"}>
        {JSON.stringify(value)}
      </span>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-neutral-600 dark:text-neutral-400">[]</span>;
    return (
      <span>
        <button onClick={() => setCollapsed((v) => !v)} className="text-neutral-600 dark:text-neutral-400 hover:text-neutral-700 mr-1">
          {collapsed ? "▶" : "▼"}
        </button>
        {collapsed ? (
          <span className="text-neutral-600 dark:text-neutral-400">[{value.length} items]</span>
        ) : (
          <ul className="ml-4 border-l border-neutral-200 dark:border-neutral-700 pl-2">
            {value.slice(0, 20).map((item, i) => (
              <li key={i}>
                <span className="text-neutral-600 dark:text-neutral-400">{i}: </span>
                <JsonTree value={item} depth={depth + 1} />
              </li>
            ))}
            {value.length > 20 && <li className="text-neutral-600 dark:text-neutral-400 text-xs">…{value.length - 20} more</li>}
          </ul>
        )}
      </span>
    );
  }

  const entries = Object.entries(value as Record<string, unknown>);
  if (entries.length === 0) return <span className="text-neutral-600 dark:text-neutral-400">{"{}"}</span>;

  return (
    <span>
      <button onClick={() => setCollapsed((v) => !v)} className="text-neutral-600 dark:text-neutral-400 hover:text-neutral-700 mr-1">
        {collapsed ? "▶" : "▼"}
      </button>
      {collapsed ? (
        <span className="text-neutral-600 dark:text-neutral-400">{"{…}"}</span>
      ) : (
        <ul className="ml-4 border-l border-neutral-200 dark:border-neutral-700 pl-2">
          {entries.map(([k, v]) => (
            <li key={k}>
              <span className={`text-xs font-mono ${HIGHLIGHTED_KEYS.has(k) ? "text-[color:var(--c-accent)] font-semibold" : "text-neutral-600 dark:text-neutral-400"}`}>
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
