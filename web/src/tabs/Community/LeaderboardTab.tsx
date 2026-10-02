/** The leaderboard: top people by points (nicknames only), for everyone or one city, with how points work. */
import { useEffect, useState } from "react";
import { Reveal } from "../../components/shell/Reveal";
import { useSmoothScroll } from "../../hooks/useSmoothScroll";
import { CITIES } from "../../community/NicknameDialog";
import {
  fetchBoard, fetchChallenge, HOW_POINTS_WORK, SCOPE_LABEL, type Board, type BoardScope, type Challenge,
} from "../../community/points";
import { useCommunity } from "../../community/store";

const card = { background: "var(--c-surface)", border: "1px solid var(--c-border)" } as const;

function Segment({ options, value, onChange }: { options: { id: string; label: string }[]; value: string; onChange: (id: string) => void }) {
  return (
    <div className="inline-flex rounded-lg p-0.5" style={{ background: "var(--c-raised)", border: "1px solid var(--c-border)" }} role="group">
      {options.map((o) => (
        <button key={o.id} onClick={() => onChange(o.id)} aria-pressed={value === o.id} className="px-3 py-1.5 rounded-md text-sm"
                style={{ background: value === o.id ? "var(--c-accent)" : "transparent", color: value === o.id ? "var(--c-on-accent)" : "var(--c-muted)", fontWeight: value === o.id ? 600 : 400 }}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function LeaderboardTab() {
  const scrollRef = useSmoothScroll();
  const signedIn = useCommunity((s) => s.signedIn);
  const profile = useCommunity((s) => s.profile);
  const [scope, setScope] = useState<BoardScope>("all");
  const [city, setCity] = useState<string>("");
  const [board, setBoard] = useState<Board | null>(null);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setBoard(null);
    fetchBoard(scope, city || null, signedIn)
      .then((b) => { if (live) { setBoard(b); setError(null); } })
      .catch((e: Error) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [scope, city, signedIn, profile]);

  useEffect(() => { fetchChallenge().then(setChallenge).catch(() => undefined); }, []);

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto" style={{ background: "var(--c-canvas)" }}>
      <div className="max-w-3xl mx-auto px-6 py-8 flex flex-col gap-6">
        <Reveal>
          <h1 className="font-display text-4xl" style={{ fontWeight: 500 }}>Leaderboard</h1>
          <p className="mt-1" style={{ color: "var(--c-muted)" }}>
            People who report what they see at streams. Only nicknames are shown, and only for people who chose to appear.
          </p>
        </Reveal>

        {challenge && (
          <Reveal delay={40}>
            <div className="rounded-xl p-4" style={card}>
              <span className="text-sm" style={{ color: "var(--c-muted2)" }}>This week's challenge · +20 points: </span>
              <strong>{challenge.title}.</strong> <span style={{ color: "var(--c-muted)" }}>{challenge.description}</span>
            </div>
          </Reveal>
        )}

        <Reveal delay={80}>
          <div className="flex gap-3 flex-wrap items-center">
            <Segment value={scope} onChange={(id) => setScope(id as BoardScope)}
                     options={(Object.keys(SCOPE_LABEL) as BoardScope[]).map((id) => ({ id, label: SCOPE_LABEL[id] }))} />
            <label className="flex items-center gap-2 text-sm" style={{ color: "var(--c-muted)" }}>
              City
              <select value={city} onChange={(e) => setCity(e.target.value)} className="px-2.5 py-1.5 rounded-lg"
                      style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)", color: "var(--c-text)" }}>
                <option value="">All cities</option>
                {CITIES.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
          </div>
        </Reveal>

        {error && <p role="alert" style={{ color: "var(--c-danger-text)" }}>{error}</p>}
        {!board && !error && <p style={{ color: "var(--c-muted)" }}>Loading…</p>}
        {board && board.entries.length === 0 && (
          <div className="rounded-xl p-6" style={card}>
            <p>No one has points {scope === "all" ? "yet" : "in this period"}{city ? " in this city" : ""}. Be the first: file a report from the Stream map.</p>
          </div>
        )}
        {board && board.entries.length > 0 && (
          <ol className="rounded-xl overflow-hidden" style={card}>
            {board.entries.map((e, i) => (
              <li key={`${e.rank}-${e.nickname}`} className="flex items-center gap-4 px-4 py-3"
                  style={{ borderTop: i === 0 ? "none" : "1px solid var(--c-border-subtle)", background: e.is_me ? "var(--c-accent-tint)" : "transparent" }}>
                <span className="w-8 font-display text-xl text-center" style={{ fontWeight: 500 }}>{e.rank}</span>
                <span className="flex-1 font-medium">{e.nickname}{e.is_me && <span className="text-sm font-normal" style={{ color: "var(--c-accent)" }}> (you)</span>}</span>
                <span className="text-sm hidden sm:inline" style={{ color: "var(--c-muted2)" }}>
                  {e.reports} {e.reports === 1 ? "report" : "reports"} · {e.badges} {e.badges === 1 ? "badge" : "badges"}
                </span>
                <span className="font-semibold w-20 text-right">{e.points} pts</span>
              </li>
            ))}
          </ol>
        )}
        {board?.me && !board.entries.some((e) => e.is_me) && (
          <p className="text-sm" style={{ color: "var(--c-muted)" }}>
            {board.me.listed
              ? `You are #${board.me.rank} with ${board.me.points} points.`
              : `You are #${board.me.rank} with ${board.me.points} points. You chose not to appear on the leaderboard (change this in your profile).`}
          </p>
        )}

        <Reveal delay={120}>
          <details className="rounded-xl p-5" style={card}>
            <summary className="font-semibold cursor-pointer">How points work</summary>
            <ul className="mt-3 flex flex-col gap-1.5 list-disc pl-5" style={{ color: "var(--c-muted)" }}>
              {HOW_POINTS_WORK.map((line) => <li key={line}>{line}</li>)}
            </ul>
          </details>
        </Reveal>
      </div>
    </div>
  );
}
