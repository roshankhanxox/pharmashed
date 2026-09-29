/**
 * Empty state for the Explore inspector: instead of a blank panel, list the highest-priority
 * sites for the current drug and city filters. Clicking a row selects the site, same as
 * clicking its glow on the map.
 */
import { useStore } from "../../data/store";
import { TIER_LABEL, TIER_LEGEND, tierOf } from "../../data/copy";

const TIER_COLOR = { high: "#ef4444", medium: "#f59e0b", low: "#22c55e" } as const;
const ROWS = 6;

interface Row {
  siteId: string;
  city: string;
  score: number;
  tie: number;
  detail: string;
}

export function TopSitesPanel() {
  const results = useStore((s) => s.results);
  const sites = useStore((s) => s.sites);
  const drug = useStore((s) => s.selectedDrug);
  const city = useStore((s) => s.selectedCity);
  const citizen = useStore((s) => s.audience) === "citizen";
  const setSelectedSiteId = useStore((s) => s.setSelectedSiteId);
  const setSelectedCity = useStore((s) => s.setSelectedCity);
  if (!results) return null;

  const cityName = (id: string) => sites?.cities.find((c) => c.id === id)?.name ?? id;

  // One row per site: its overall score (all drugs) or the score for the chosen drug.
  const rows: Row[] =
    drug === "all"
      ? (results.site_overall ?? []).map((o) => ({
          siteId: o.site_id, city: o.site_id.split("-")[0], score: o.score, tie: 0, detail: o.top_drug,
        }))
      : results.results
          .filter((r) => r.drug === drug)
          .map((r) => ({
            siteId: r.site_id, city: r.site_id.split("-")[0], score: r.score, tie: r.rq.p50, detail: r.drug,
          }));

  const top = rows
    .filter((r) => !city || r.city === city)
    .sort((a, b) => b.score - a.score || b.tie - a.tie || a.siteId.localeCompare(b.siteId))
    .slice(0, ROWS);

  const where = city ? cityName(city) : "all five cities";
  const what = drug === "all" ? "all medicines" : drug;

  function pick(row: Row) {
    setSelectedSiteId(row.siteId);
    setSelectedCity(row.city);
  }

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="font-display text-2xl mb-1" style={{ fontWeight: 500, color: "var(--c-text)" }}>
        {citizen ? "Where to test first" : "Highest-priority sites"}
      </h2>
      <p className="text-sm mb-4" style={{ color: "var(--c-muted2)" }}>
        {what} · {where}. {citizen ? "Tap a place, or a glow on the map." : "Click a row, or a glow on the map."}
      </p>

      <ul className="rounded-xl overflow-hidden" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
        {top.map((r, i) => {
          const tier = tierOf(r.score);
          return (
            <li key={r.siteId} style={{ borderTop: i === 0 ? "none" : "1px solid var(--c-border-subtle)" }}>
              <button
                onClick={() => pick(r)}
                className="w-full flex items-center gap-3 px-4 py-3 text-left"
                style={{ color: "var(--c-text)" }}
              >
                <span className="inline-block w-3.5 h-3.5 rounded-full shrink-0" style={{ background: TIER_COLOR[tier] }} />
                <span className="flex-1 min-w-0">
                  <span className="font-medium">{cityName(r.city)}</span>
                  <span className="text-sm" style={{ color: "var(--c-muted2)" }}> · site {r.siteId}</span>
                </span>
                <span className="text-sm shrink-0" style={{ color: "var(--c-muted)" }}>
                  {citizen ? TIER_LABEL[tier] : `${r.score.toFixed(3)} · ${tier}`}
                </span>
              </button>
            </li>
          );
        })}
        {top.length === 0 && (
          <li className="px-4 py-3 text-sm" style={{ color: "var(--c-muted)" }}>No sites for this selection.</li>
        )}
      </ul>

      <p className="text-sm leading-relaxed mt-5" style={{ color: "var(--c-muted2)" }}>
        {citizen
          ? `Colours: red = ${TIER_LEGEND.high.toLowerCase()}, amber = ${TIER_LEGEND.medium.toLowerCase()}, green = ${TIER_LEGEND.low.toLowerCase()}.`
          : "Sites are ranked by sampling priority score: the share of Monte Carlo draws where the risk quotient RQ exceeds 1. High ≥ 0.5, medium ≥ 0.1. Sites can tie when their scores saturate near 1; ties are ordered by median RQ."}
      </p>
    </div>
  );
}
