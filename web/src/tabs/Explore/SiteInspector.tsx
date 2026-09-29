import { useStore } from "../../data/store";
import { BandChart, type BandRow } from "../../components/charts/BandChart";
import { DrawHistogram } from "../../components/charts/DrawHistogram";
import { Tornado } from "../../components/charts/Tornado";
import { Term } from "../../components/glossary/Term";
import { CitizenSiteCard } from "./CitizenSiteCard";
import { TopSitesPanel } from "./TopSitesPanel";

const C = {
  canvas:  "var(--c-canvas)",
  surface: "var(--c-surface)",
  raised:  "var(--c-raised)",
  border:  "var(--c-border)",
  text:    "var(--c-text)",
  muted:   "var(--c-muted)",
  faint:   "var(--c-faint)",
  indigo:  "var(--c-accent)",
} as const;

export function SiteInspector() {
  const results        = useStore((s) => s.results);
  const selectedSiteId = useStore((s) => s.selectedSiteId);
  const expandedDrug   = useStore((s) => s.expandedDrug);
  const setExpandedDrug = useStore((s) => s.setExpandedDrug);
  const audience       = useStore((s) => s.audience);
  const openAssistantFor = useStore((s) => s.openAssistantFor);

  // Nothing selected yet: show the highest-priority sites instead of a blank panel.
  if (!results) return null;
  if (!selectedSiteId) return <TopSitesPanel />;

  if (audience === "citizen") return <CitizenSiteCard siteId={selectedSiteId} />;

  const siteResults = results.results
    .filter((r) => r.site_id === selectedSiteId)
    .sort((a, b) => b.rq.p50 - a.rq.p50);

  if (siteResults.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm" style={{ color: C.faint }}>
        No results for site {selectedSiteId}.
      </div>
    );
  }

  const first   = siteResults[0];
  const overall = results.site_overall?.find((s) => s.site_id === selectedSiteId);

  const bandRows: BandRow[] = siteResults.map((r) => ({
    drug:         r.drug,
    p5:           r.pec_ng_l.p5,
    p50:          r.pec_ng_l.p50,
    p95:          r.pec_ng_l.p95,
    pnec:         r.pnec_ng_l,
    lod:          r.lod_ng_l ?? null,
    score:        r.score,
    tier:         r.tier,
    pnecProvKey:  r.provenance_keys.find((k) => k.startsWith("pnec:")),
    lodProvKey:   r.provenance_keys.find((k) => k.startsWith("lod:")),
  }));

  const expanded = siteResults.find((r) => r.drug === expandedDrug);

  return (
    <div className="flex flex-col p-5 gap-5" style={{ background: C.canvas }}>

      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h2 className="text-base font-semibold" style={{ color: C.text }}>
              {selectedSiteId}
            </h2>
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{ background: "var(--c-warn-bg)", color: "var(--c-warn-text)", border: "1px solid var(--c-warn-border)" }}
            >
              Illustrative
            </span>
            {overall && (
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{ background: C.surface, color: C.muted, border: `1px solid ${C.border}` }}
              >
                #{overall.rank_in_city} of {first.n_in_city} in {selectedSiteId.split("-")[0]}
              </span>
            )}
          </div>
          <p className="text-xs" style={{ color: C.faint }}>
            Top drug:{" "}
            <strong style={{ color: C.muted }}>{overall?.top_drug ?? first.drug}</strong>
            {" · "}
            <Term term="score">sampling priority score</Term>{" "}
            <strong style={{ color: C.indigo }}>{(overall?.score ?? first.score).toFixed(3)}</strong>
            {" "}under stated priors
          </p>
        </div>
        <button
          onClick={() => openAssistantFor(selectedSiteId, expandedDrug)}
          className="shrink-0 px-3.5 py-2 text-sm font-semibold rounded-lg"
          style={{ background: C.indigo, color: "#fff" }}
        >
          Ask about this site
        </button>
      </div>

      {/* BandChart */}
      <div>
        <div
          className="text-xs font-semibold uppercase mb-2"
          style={{ color: C.faint, letterSpacing: "0.05em" }}
        >
          Predicted concentrations · click a drug row to expand
        </div>
        <BandChart
          rows={bandRows}
          onRowClick={(drug) => setExpandedDrug(expandedDrug === drug ? null : drug)}
          expandedDrug={expandedDrug}
        />
      </div>

      {/* Expanded drug details */}
      {expanded && (
        <div
          className="rounded-xl p-4 flex flex-col gap-4"
          style={{ background: C.surface, border: `1px solid ${C.border}` }}
        >
          <div>
            <div
              className="text-xs font-semibold uppercase mb-2"
              style={{ color: C.faint, letterSpacing: "0.05em" }}
            >
              {expanded.drug} — draw distribution
            </div>
            <DrawHistogram histogram={expanded.histogram} score={expanded.score} />
          </div>

          {expanded.drivers?.length > 0 && (
            <div>
              <div
                className="text-xs font-semibold uppercase mb-2"
                style={{ color: C.faint, letterSpacing: "0.05em" }}
              >
                Sensitivity — Spearman ρ
              </div>
              <Tornado drivers={expanded.drivers} driverSentence={expanded.driver_sentence} />
            </div>
          )}

          {expanded.flip && (
            <div
              className="rounded-lg px-3 py-2.5 text-xs leading-relaxed"
              style={{ background: C.raised, border: `1px solid ${C.border}`, color: C.muted }}
            >
              <span className="font-semibold" style={{ color: C.text }}>Tier flip: </span>
              {expanded.flip.down && (
                <span>
                  drops to{" "}
                  <strong style={{ color: C.muted }}>{expanded.flip.down.to_tier}</strong>
                  {" "}if {expanded.flip.down.param} × {expanded.flip.down.multiplier}
                </span>
              )}
              {expanded.flip.down && expanded.flip.up && <span> · </span>}
              {expanded.flip.up && (
                <span>
                  rises to{" "}
                  <strong style={{ color: C.muted }}>{expanded.flip.up.to_tier}</strong>
                  {" "}if {expanded.flip.up.param} × {expanded.flip.up.multiplier}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
