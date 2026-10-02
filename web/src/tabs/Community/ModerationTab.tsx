/** Moderator queue: reports that are held or flagged, with why, and Approve / Hide. Only shown to moderators. */
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../community/api";
import { ago, checklistPairs, type Report } from "../../community/reports";
import { useSmoothScroll } from "../../hooks/useSmoothScroll";
import { outlineButton } from "../../community/Modal";

interface QueueItem extends Report {
  nickname: string | null;
  note_raw: string;
  why: string[];
  flags: { reason: string; label: string }[];
  photo_preview: string | null;
}

const card = { background: "var(--c-surface)", border: "1px solid var(--c-border)" } as const;

export function ModerationTab() {
  const scrollRef = useSmoothScroll();
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    apiFetch<QueueItem[]>("/admin/reports", { auth: true })
      .then((q) => { setItems(q); setError(null); })
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function decide(id: string, action: "approve" | "hide") {
    setBusyId(id);
    try {
      await apiFetch(`/admin/reports/${id}/${action}`, { method: "POST", auth: true, body: JSON.stringify({ note: notes[id] ?? "" }) });
      setItems((cur) => (cur ?? []).filter((i) => i.id !== id));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto" style={{ background: "var(--c-canvas)" }}>
      <div className="max-w-3xl mx-auto px-6 py-8 flex flex-col gap-5">
        <div>
          <h1 className="font-display text-4xl" style={{ fontWeight: 500 }}>Moderation</h1>
          <p className="mt-1" style={{ color: "var(--c-muted)" }}>
            Reports held for review or flagged by readers. Approving makes a report public and scores it. Hiding removes it from the map, takes back its points and deletes its photo.
          </p>
        </div>
        {error && <p role="alert" style={{ color: "var(--c-danger-text)" }}>{error}</p>}
        {!items && !error && <p style={{ color: "var(--c-muted)" }}>Loading…</p>}
        {items?.length === 0 && <div className="rounded-xl p-6" style={card}>Nothing waiting. All reports are reviewed.</div>}
        {items?.map((r) => (
          <article key={r.id} className="rounded-xl p-5 flex flex-col gap-3" style={card}>
            <header className="text-sm flex flex-wrap gap-x-2" style={{ color: "var(--c-muted2)" }}>
              <span className="font-medium" style={{ color: "var(--c-text)" }}>{r.nickname ?? "Unknown"}</span>
              <span>· {r.site_id ? `Site ${r.site_id}` : "Outside our sites"}</span>
              <span>· visited {ago(r.observed_at)}</span>
              <span>· {r.status === "pending" ? "Held" : "Public"}</span>
            </header>
            <ul className="text-sm list-disc pl-5" style={{ color: "var(--c-warn-text)" }}>
              {r.why.map((w) => <li key={w}>{w}</li>)}
            </ul>
            {r.flags.length > 0 && <div className="text-sm" style={{ color: "var(--c-muted)" }}>Reasons given: {r.flags.map((f) => f.label).join("; ")}</div>}
            <div className="text-sm">
              {checklistPairs(r.checklist).map(([q, a], i) => (
                <span key={q}>{i > 0 && " · "}<strong>{q}:</strong> {a}</span>
              ))}
            </div>
            {r.note_raw && <p className="text-sm italic">“{r.note_raw}”</p>}
            {r.photo_preview && <img src={r.photo_preview} alt="Report photo" className="max-w-xs rounded-lg" style={{ border: "1px solid var(--c-border)" }} />}
            <input value={notes[r.id] ?? ""} onChange={(e) => setNotes({ ...notes, [r.id]: e.target.value })} maxLength={300}
                   placeholder="Note (optional, kept in the log)" className="px-3 py-2 rounded-lg text-sm"
                   style={{ background: "var(--c-canvas)", border: "1px solid var(--c-border)", color: "var(--c-text)" }} />
            <div className="flex gap-2">
              <button disabled={busyId === r.id} onClick={() => void decide(r.id, "approve")} className="px-4 py-2 rounded-lg font-semibold disabled:opacity-50"
                      style={{ background: "var(--c-accent)", color: "var(--c-on-accent)" }}>Approve</button>
              <button disabled={busyId === r.id} onClick={() => void decide(r.id, "hide")} className="px-4 py-2 rounded-lg font-semibold disabled:opacity-50"
                      style={{ background: "var(--c-danger-bg)", color: "var(--c-danger-text)", border: "1px solid var(--c-danger-border)" }}>Hide</button>
              <button onClick={load} className="px-4 py-2 rounded-lg font-medium" style={outlineButton}>Refresh</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
