/** The report form: where, what you saw, an optional note. Sent reports are public, unverified, and never change a score. */
import { useMemo, useState, type FormEvent } from "react";
import { useStore } from "../data/store";
import { ErrorLine, Modal, outlineButton, primaryButton } from "./Modal";
import { hasAnswers, nearestSite, NOTE_MAX, QUESTIONS, type Checklist } from "./reports";
import { useReports } from "./reportsStore";

/** `datetime-local` wants local time without a zone: "2026-06-01T14:30". */
const localInput = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);

function Chip({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className="px-3 py-1.5 rounded-full text-sm"
      style={{
        border: `1px solid ${selected ? "var(--c-accent)" : "var(--c-border)"}`,
        background: selected ? "var(--c-accent-tint)" : "var(--c-surface)",
        color: selected ? "var(--c-accent)" : "var(--c-muted)",
        fontWeight: selected ? 600 : 400,
      }}
    >
      {children}
    </button>
  );
}

export function ReportDialog() {
  const { dialogOpen, spot, busy, error, justSent } = useReports();
  const { cancel, startPicking, pickSpot, submit } = useReports.getState();
  const sites = useStore((s) => s.sites);
  const [answers, setAnswers] = useState<Checklist>({});
  const [note, setNote] = useState("");
  const [when, setWhen] = useState(() => localInput(new Date()));
  const [locError, setLocError] = useState<string | null>(null);
  const linked = useMemo(() => (spot && sites ? nearestSite(spot, sites.sites) : null), [spot, sites]);

  if (!dialogOpen) return null;

  if (justSent) {
    return (
      <Modal title="Thank you" onClose={cancel}>
        <p className="mb-4" style={{ color: "var(--c-muted)" }}>
          Your report is on the map{justSent.site_id ? ` and on the page for site ${justSent.site_id}` : ""}. It is shown as
          unverified and does not change any testing priority.
        </p>
        <button onClick={cancel} className="w-full px-4 py-2.5 rounded-lg font-semibold" style={primaryButton}>Done</button>
      </Modal>
    );
  }

  const choose = (key: string, value: string, multi?: boolean) =>
    setAnswers((a) => {
      if (multi) {
        const list = (a[key] as string[] | undefined) ?? [];
        return { ...a, [key]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value] };
      }
      return { ...a, [key]: a[key] === value ? "" : value }; // tap again to clear
    });

  function useMyLocation() {
    setLocError(null);
    if (!navigator.geolocation) return setLocError("Your browser cannot share its location.");
    navigator.geolocation.getCurrentPosition(
      (p) => pickSpot({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => setLocError("Could not get your location. Choose the spot on the map instead."),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const ok = await submit({ observed_at: new Date(when).toISOString(), checklist: answers, note: note.trim() });
    if (ok) {
      setAnswers({});
      setNote("");
      setWhen(localInput(new Date()));
    }
  }

  return (
    <Modal title="Report what you see" onClose={cancel}>
      <form onSubmit={onSubmit}>
        <div className="mb-5">
          <div className="text-sm font-medium mb-1">Where</div>
          {spot ? (
            <p className="text-sm mb-2" style={{ color: "var(--c-muted)" }}>
              {linked
                ? `Close to site ${linked.id} (about ${linked.metres} m away).`
                : "Not near one of our sites: it will still show on the map."}
            </p>
          ) : (
            <p className="text-sm mb-2" style={{ color: "var(--c-muted)" }}>Choose the spot where you are looking at the stream.</p>
          )}
          <div className="flex gap-2 flex-wrap">
            <button type="button" onClick={startPicking} className="px-3 py-1.5 rounded-lg text-sm font-medium" style={outlineButton}>
              {spot ? "Change spot on the map" : "Choose on the map"}
            </button>
            <button type="button" onClick={useMyLocation} className="px-3 py-1.5 rounded-lg text-sm font-medium" style={outlineButton}>
              Use my location
            </button>
          </div>
          {locError && <p className="text-sm mt-2" style={{ color: "var(--c-danger-text)" }}>{locError}</p>}
        </div>

        <label className="block mb-5">
          <span className="block text-sm font-medium mb-1">When did you visit?</span>
          <input
            type="datetime-local"
            value={when}
            max={localInput(new Date())}
            onChange={(e) => setWhen(e.target.value)}
            className="px-3 py-2 rounded-lg text-base"
            style={{ background: "var(--c-canvas)", border: "1px solid var(--c-border)", color: "var(--c-text)" }}
          />
        </label>

        <p className="text-sm mb-3" style={{ color: "var(--c-muted2)" }}>Answer whatever you noticed. Skip the rest.</p>
        {QUESTIONS.map((q) => (
          <fieldset key={q.key} className="mb-4">
            <legend className="text-sm font-medium mb-1.5">{q.label}</legend>
            <div className="flex flex-wrap gap-2">
              {q.options.map((o) => {
                const value = answers[q.key];
                const selected = Array.isArray(value) ? value.includes(o.value) : value === o.value;
                return <Chip key={o.value} selected={selected} onClick={() => choose(q.key, o.value, q.multi)}>{o.label}</Chip>;
              })}
            </div>
          </fieldset>
        ))}

        <label className="block mb-4">
          <span className="block text-sm font-medium mb-1">Anything else? (optional)</span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={NOTE_MAX}
            rows={3}
            className="w-full px-3 py-2 rounded-lg text-base"
            style={{ background: "var(--c-canvas)", border: "1px solid var(--c-border)", color: "var(--c-text)" }}
          />
          <span className="block text-sm mt-1" style={{ color: "var(--c-muted2)" }}>
            {note.length}/{NOTE_MAX}. No links or personal details, please.
          </span>
        </label>

        <p className="text-sm mb-4" style={{ color: "var(--c-muted2)" }}>
          Your nickname will show next to the report. Reports are unverified and never change a testing priority.
        </p>
        <ErrorLine message={error} />
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={busy || !spot || !hasAnswers(answers)}
            className="flex-1 px-4 py-2.5 rounded-lg font-semibold disabled:opacity-50"
            style={primaryButton}
          >
            {busy ? "Sending…" : "Send report"}
          </button>
          <button type="button" onClick={cancel} className="px-4 py-2.5 rounded-lg font-medium" style={outlineButton}>Cancel</button>
        </div>
      </form>
    </Modal>
  );
}
