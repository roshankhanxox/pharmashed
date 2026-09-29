/**
 * Plain-language site summary for citizen view: a testing-priority label, one sentence of
 * explanation, and a ranked list of medicines with what each is used for. No scores,
 * concentrations or model terms; expert view keeps those.
 */
import { useStore } from "../../data/store";
import {
  DEMO_NOTICE, DRUG_USE, SCORE_CAVEAT, TIER_LABEL, TIER_SENTENCE, tierOf,
} from "../../data/copy";
import { Reveal } from "../../components/shell/Reveal";

const TIER_COLOR = { high: "#ef4444", medium: "#f59e0b", low: "#22c55e" } as const;

export function CitizenSiteCard({ siteId }: { siteId: string }) {
  const results = useStore((s) => s.results);
  const sites = useStore((s) => s.sites);
  const setAudience = useStore((s) => s.setAudience);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const openAssistantFor = useStore((s) => s.openAssistantFor);
  if (!results) return null;

  const drugs = results.results
    .filter((r) => r.site_id === siteId)
    .sort((a, b) => b.score - a.score);
  if (drugs.length === 0) return null;

  const overall = results.site_overall?.find((s) => s.site_id === siteId);
  const topScore = overall?.score ?? drugs[0].score;
  const tier = tierOf(topScore);
  const topDrug = overall?.top_drug ?? drugs[0].drug;
  const cityId = siteId.split("-")[0];
  const cityName = sites?.cities.find((c) => c.id === cityId)?.name ?? cityId;

  return (
    <div className="flex flex-col gap-5 p-6 max-w-2xl">
      <Reveal>
        <div>
          <div className="text-sm mb-1" style={{ color: "var(--c-muted2)" }}>{cityName} · site {siteId}</div>
          <h2 className="font-display text-3xl mb-3" style={{ fontWeight: 500 }}>Testing priority</h2>
          <div className="flex items-center gap-3 mb-3">
            <span className="inline-block w-5 h-5 rounded-full" style={{ background: TIER_COLOR[tier] }} />
            <span className="text-xl font-semibold">{TIER_LABEL[tier]}</span>
            {overall && (
              <span className="text-sm px-2 py-0.5 rounded" style={{ background: "var(--c-raised)", color: "var(--c-muted)", border: "1px solid var(--c-border)" }}>
                #{overall.rank_in_city} of {drugs[0].n_in_city} in {cityName}
              </span>
            )}
          </div>
          <p className="text-base leading-relaxed" style={{ color: "var(--c-muted)" }}>{TIER_SENTENCE[tier]}</p>
        </div>
      </Reveal>

      <Reveal delay={80}>
        <div className="rounded-xl p-5" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
          <h3 className="font-semibold mb-1">Medicines, from highest to lowest priority here</h3>
          <p className="text-sm mb-3" style={{ color: "var(--c-muted2)" }}>
            Top of the list: <strong style={{ color: "var(--c-text)" }}>{topDrug}</strong>
          </p>
          <ul className="flex flex-col">
            {drugs.map((d, i) => (
              <li
                key={d.drug}
                className="flex items-center gap-3 py-2.5"
                style={{ borderTop: i === 0 ? "none" : "1px solid var(--c-border-subtle)" }}
              >
                <span className="inline-block w-3.5 h-3.5 rounded-full shrink-0" style={{ background: TIER_COLOR[tierOf(d.score)] }} />
                <span className="flex-1">
                  <span className="font-medium capitalize">{d.drug}</span>
                  <span className="text-sm" style={{ color: "var(--c-muted2)" }}> · {DRUG_USE[d.drug] ?? "medicine"}</span>
                </span>
                <span className="text-sm" style={{ color: "var(--c-muted)" }}>{TIER_LABEL[tierOf(d.score)]}</span>
              </li>
            ))}
          </ul>
        </div>
      </Reveal>

      <Reveal delay={160}>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => openAssistantFor(siteId)}
            className="px-5 py-2.5 rounded-lg font-semibold"
            style={{ background: "var(--c-accent)", color: "var(--c-on-accent)" }}
          >
            Ask about this site
          </button>
          <button
            onClick={() => setActiveTab("scenarios")}
            className="px-5 py-2.5 rounded-lg font-medium"
            style={{ border: "1px solid var(--c-border)", background: "var(--c-surface)", color: "var(--c-text)" }}
          >
            What if something changed?
          </button>
        </div>
      </Reveal>

      <Reveal delay={200}>
        <div className="text-sm leading-relaxed flex flex-col gap-1.5" style={{ color: "var(--c-muted2)" }}>
          <p>{SCORE_CAVEAT}</p>
          <p>{DEMO_NOTICE}</p>
          <p>
            Want the charts and numbers?{" "}
            <button onClick={() => setAudience("expert")} className="underline font-medium" style={{ color: "var(--c-accent)" }}>
              Switch to Expert view
            </button>
          </p>
        </div>
      </Reveal>
    </div>
  );
}
