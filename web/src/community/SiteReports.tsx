/** Recent citizen reports for one site, plus the button to file one. Shown in both views of the site page. */
import { useStore } from "../data/store";
import { useCommunity } from "./store";
import { ago, describeChecklist } from "./reports";
import { useReports } from "./reportsStore";
import { startReportFlow } from "./startReport";

export function SiteReports({ siteId }: { siteId: string }) {
  const available = useCommunity((s) => s.availability === "ready");
  const all = useReports((s) => s.reports);
  const reports = all.filter((r) => r.site_id === siteId);
  const sites = useStore((s) => s.sites);
  if (!available) return null;
  const site = sites?.sites.find((s) => s.id === siteId);

  return (
    <div className="rounded-xl p-5" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
      <div className="flex items-start justify-between gap-3 mb-1">
        <h3 className="font-semibold">What people have seen here</h3>
        <button
          onClick={() => startReportFlow(site ? { lat: site.lonlat[1], lon: site.lonlat[0] } : null)}
          className="px-3 py-1.5 rounded-lg text-sm font-semibold shrink-0"
          style={{ background: "var(--c-accent)", color: "var(--c-on-accent)" }}
        >
          Report this site
        </button>
      </div>
      <p className="text-sm mb-3" style={{ color: "var(--c-muted2)" }}>
        Citizen reports are unverified and do not change the testing priority.
      </p>
      {reports.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--c-muted)" }}>No reports yet. Be the first.</p>
      ) : (
        <ul className="flex flex-col">
          {reports.slice(0, 5).map((r, i) => (
            <li key={r.id} className="py-2.5" style={{ borderTop: i === 0 ? "none" : "1px solid var(--c-border-subtle)" }}>
              <div className="text-sm flex flex-wrap gap-x-2" style={{ color: "var(--c-muted2)" }}>
                <span className="font-medium" style={{ color: "var(--c-text)" }}>{r.author}</span>
                <span>· {ago(r.observed_at)}</span>
                {r.is_sample && <span className="px-1.5 rounded" style={{ border: "1px solid var(--c-border)" }}>sample</span>}
              </div>
              <div className="text-sm" style={{ color: "var(--c-muted)" }}>{describeChecklist(r.checklist).join(" · ")}</div>
              {r.note && <div className="text-sm italic mt-0.5" style={{ color: "var(--c-muted)" }}>“{r.note}”</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
