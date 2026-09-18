import { useStore } from "../../data/store";
import { BandChart, type BandRow } from "../../components/charts/BandChart";
import { DrawHistogram } from "../../components/charts/DrawHistogram";
import { Tornado } from "../../components/charts/Tornado";
import { Term } from "../../components/glossary/Term";
import { EmptyView } from "../../components/shell/StateViews";

export function SiteInspector() {
  const results = useStore((s) => s.results);
  const selectedSiteId = useStore((s) => s.selectedSiteId);
  const expandedDrug = useStore((s) => s.expandedDrug);
  const setExpandedDrug = useStore((s) => s.setExpandedDrug);

  if (!results || !selectedSiteId) {
    return <EmptyView reason="Select a site on the map to inspect it." />;
  }

  const siteResults = results.results
    .filter((r) => r.site_id === selectedSiteId)
    .sort((a, b) => b.rq.p50 - a.rq.p50);

  if (siteResults.length === 0) {
    return <EmptyView reason={`No results for site ${selectedSiteId}.`} />;
  }

  const first = siteResults[0];
  const overall = results.site_overall?.find((s) => s.site_id === selectedSiteId);

  const bandRows: BandRow[] = siteResults.map((r) => ({
    drug: r.drug,
    p5: r.pec_ng_l.p5,
    p50: r.pec_ng_l.p50,
    p95: r.pec_ng_l.p95,
    pnec: r.pnec_ng_l,
    lod: r.lod_ng_l ?? null,
    score: r.score,
    tier: r.tier,
    pnecProvKey: r.provenance_keys.find((k) => k.startsWith("pnec:")),
    lodProvKey: r.provenance_keys.find((k) => k.startsWith("lod:")),
  }));

  const expanded = siteResults.find((r) => r.drug === expandedDrug);

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4 gap-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-100">
              {selectedSiteId}
            </h2>
            <span className="text-xs bg-yellow-100 text-yellow-800 rounded px-1.5 py-0.5">
              Synthetic site
            </span>
            {overall && (
              <span className="text-xs bg-neutral-100 text-neutral-600 rounded px-1.5 py-0.5">
                #{overall.rank_in_city} of {first.n_in_city} in {selectedSiteId.split("-")[0]}
              </span>
            )}
          </div>
          <p className="text-xs text-neutral-400 mt-0.5">
            Top drug: <strong>{overall?.top_drug ?? first.drug}</strong> ·{" "}
            <Term term="score">sampling priority score</Term>{" "}
            {(overall?.score ?? first.score).toFixed(3)} under stated priors
          </p>
        </div>
      </div>

      {/* BandChart */}
      <div>
        <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-2">
          Predicted concentrations
        </h3>
        <BandChart
          rows={bandRows}
          onRowClick={(drug) => setExpandedDrug(expandedDrug === drug ? null : drug)}
          expandedDrug={expandedDrug}
        />
      </div>

      {/* Expanded drug details */}
      {expanded && (
        <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 flex flex-col gap-4 bg-neutral-50 dark:bg-neutral-900">
          <div>
            <h3 className="text-sm font-medium mb-2">{expanded.drug} — draw distribution</h3>
            <DrawHistogram histogram={expanded.histogram} score={expanded.score} />
          </div>

          {expanded.drivers?.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2">Sensitivity (Spearman ρ)</h3>
              <Tornado drivers={expanded.drivers} driverSentence={expanded.driver_sentence} />
            </div>
          )}

          {expanded.flip && (
            <div className="text-xs text-neutral-500">
              <span className="font-medium">Tier change: </span>
              {expanded.flip.down && (
                <span>
                  Drops to {expanded.flip.down.to_tier} if{" "}
                  {expanded.flip.down.param} × {expanded.flip.down.multiplier}
                </span>
              )}
              {expanded.flip.down && expanded.flip.up && <span> · </span>}
              {expanded.flip.up && (
                <span>
                  Rises to {expanded.flip.up.to_tier} if{" "}
                  {expanded.flip.up.param} × {expanded.flip.up.multiplier}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
