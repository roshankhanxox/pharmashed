/** "My streams": the signed-in person's points, rank, streak, this week's challenge, badges, and reports. */
import { useEffect, useState } from "react";
import { Reveal } from "../../components/shell/Reveal";
import { useSmoothScroll } from "../../hooks/useSmoothScroll";
import { fetchMyReports, fetchProgress, signed, STATUS_LABEL, type Progress } from "../../community/points";
import { ago, describeChecklist, type Report } from "../../community/reports";
import { useCommunity } from "../../community/store";

const card = { background: "var(--c-surface)", border: "1px solid var(--c-border)" } as const;

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl p-4 flex-1 min-w-[8rem]" style={card}>
      <div className="font-display text-3xl" style={{ fontWeight: 500 }}>{value}</div>
      <div className="text-sm" style={{ color: "var(--c-muted2)" }}>{label}</div>
    </div>
  );
}

export function MyStreamsTab() {
  const scrollRef = useSmoothScroll();
  const signedIn = useCommunity((s) => s.signedIn);
  const profile = useCommunity((s) => s.profile);
  const openAuth = useCommunity((s) => s.openAuthDialog);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [mine, setMine] = useState<Report[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!signedIn) return;
    let live = true;
    Promise.all([fetchProgress(), fetchMyReports()])
      .then(([p, r]) => { if (live) { setProgress(p); setMine(r); setError(null); } })
      .catch((e: Error) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [signedIn, profile]);

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto" style={{ background: "var(--c-canvas)" }}>
      <div className="max-w-3xl mx-auto px-6 py-8 flex flex-col gap-6">
        <Reveal>
          <h1 className="font-display text-4xl" style={{ fontWeight: 500 }}>My streams</h1>
          <p className="mt-1" style={{ color: "var(--c-muted)" }}>
            Your points, badges and reports. Points reward useful, honest reports; they never change a testing priority.
          </p>
        </Reveal>

        {!signedIn && (
          <div className="rounded-xl p-6" style={card}>
            <p className="mb-3">Sign in to collect points and badges for the reports you file.</p>
            <button onClick={() => openAuth("signin")} className="px-5 py-2.5 rounded-lg font-semibold"
                    style={{ background: "var(--c-accent)", color: "var(--c-on-accent)" }}>Sign in</button>
          </div>
        )}
        {signedIn && error && <p role="alert" style={{ color: "var(--c-danger-text)" }}>{error}</p>}
        {signedIn && !progress && !error && <p style={{ color: "var(--c-muted)" }}>Loading…</p>}

        {progress && (
          <>
            <Reveal delay={60}>
              <div className="flex gap-3 flex-wrap">
                <Stat value={String(progress.points)} label="points" />
                <Stat value={progress.rank ? `#${progress.rank}` : "–"} label="rank" />
                <Stat value={String(progress.points_this_week)} label="points this week" />
                <Stat value={String(progress.streak_weeks)} label={progress.streak_weeks === 1 ? "week in a row" : "weeks in a row"} />
              </div>
            </Reveal>

            <Reveal delay={100}>
              <div className="rounded-xl p-5" style={card}>
                <div className="text-sm mb-1" style={{ color: "var(--c-muted2)" }}>This week's challenge · +20 points</div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h2 className="font-semibold text-lg">{progress.challenge.title}</h2>
                  {progress.challenge.done && (
                    <span className="text-sm px-2 py-0.5 rounded" style={{ background: "var(--c-ok-bg)", color: "var(--c-ok-text)", border: "1px solid var(--c-ok-border)" }}>
                      Done
                    </span>
                  )}
                </div>
                <p style={{ color: "var(--c-muted)" }}>{progress.challenge.description}</p>
              </div>
            </Reveal>

            <Reveal delay={140}>
              <h2 className="font-semibold text-lg mb-2">Badges</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                {progress.badges.map((b) => (
                  <div key={b.key} className="rounded-xl p-4 flex gap-3 items-start" style={{ ...card, opacity: b.earned ? 1 : 0.6 }}>
                    <span aria-hidden className="w-9 h-9 rounded-full flex items-center justify-center text-lg shrink-0"
                          style={{ background: b.earned ? "var(--c-accent)" : "var(--c-raised)", color: b.earned ? "var(--c-on-accent)" : "var(--c-faint)" }}>
                      {b.earned ? "✓" : "·"}
                    </span>
                    <div>
                      <div className="font-medium">{b.title}</div>
                      <div className="text-sm" style={{ color: "var(--c-muted2)" }}>{b.earned ? b.description : `To earn: ${b.description.toLowerCase()}`}</div>
                    </div>
                  </div>
                ))}
              </div>
            </Reveal>

            <Reveal delay={180}>
              <h2 className="font-semibold text-lg mb-2">Recent points</h2>
              {progress.recent.length === 0 ? (
                <p style={{ color: "var(--c-muted)" }}>Nothing yet. File a report from the Stream map.</p>
              ) : (
                <ul className="rounded-xl" style={card}>
                  {progress.recent.map((e, i) => (
                    <li key={i} className="flex items-baseline gap-3 px-4 py-2.5" style={{ borderTop: i === 0 ? "none" : "1px solid var(--c-border-subtle)" }}>
                      <span className="font-semibold w-10 shrink-0" style={{ color: e.points < 0 ? "var(--c-danger-text)" : e.points === 0 ? "var(--c-muted2)" : "var(--c-accent)" }}>{signed(e.points)}</span>
                      <span className="flex-1">{e.reversed ? `Removed: ${e.label}` : e.label}{e.site_id ? ` · ${e.site_id}` : ""}</span>
                      <span className="text-sm" style={{ color: "var(--c-muted2)" }}>{ago(e.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Reveal>

            <Reveal delay={220}>
              <h2 className="font-semibold text-lg mb-2">My reports</h2>
              {mine.length === 0 ? (
                <p style={{ color: "var(--c-muted)" }}>You have not filed a report yet.</p>
              ) : (
                <ul className="rounded-xl" style={card}>
                  {mine.map((r, i) => (
                    <li key={r.id} className="px-4 py-3" style={{ borderTop: i === 0 ? "none" : "1px solid var(--c-border-subtle)" }}>
                      <div className="text-sm flex flex-wrap gap-x-2" style={{ color: "var(--c-muted2)" }}>
                        <span className="font-medium" style={{ color: "var(--c-text)" }}>{r.site_id ? `Site ${r.site_id}` : "Outside our sites"}</span>
                        <span>· {ago(r.observed_at)}</span>
                        <span>· {STATUS_LABEL[r.status ?? "approved"]}</span>
                      </div>
                      <div className="text-sm" style={{ color: "var(--c-muted)" }}>{describeChecklist(r.checklist).join(" · ")}</div>
                    </li>
                  ))}
                </ul>
              )}
            </Reveal>
          </>
        )}
      </div>
    </div>
  );
}
