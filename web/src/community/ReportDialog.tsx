/** The report form, in three short steps: where and when, what you saw, then a note and send.
 * Sent reports are public, unverified, and never change a score. */
import { useEffect, useMemo, useRef, useState } from "react";
import { useStore } from "../data/store";
import { ErrorLine, Modal, outlineButton, primaryButton } from "./Modal";
import { useCommunity } from "./store";
import {
  describeChecklist, hasAnswers, nearestSite, NOTE_MAX, photoFlagMessage, proofreadNote, QUESTIONS, shrinkImage,
  uploadPhoto, type Checklist, type PhotoUpload, type Proofread,
} from "./reports";
import { useReports } from "./reportsStore";

/** `datetime-local` wants local time without a zone: "2026-06-01T14:30". */
const localInput = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);

const STEPS = ["Where and when", "What you saw", "Note and send"] as const;

function Chip({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className="px-2.5 py-1 rounded-full text-sm"
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

function Progress({ step }: { step: number }) {
  return (
    <div className="mb-5" aria-label={`Step ${step + 1} of ${STEPS.length}: ${STEPS[step]}`}>
      <div className="flex gap-1.5 mb-2">
        {STEPS.map((name, i) => (
          <span key={name} className="h-1.5 flex-1 rounded-full" style={{ background: i <= step ? "var(--c-accent)" : "var(--c-border)" }} />
        ))}
      </div>
      <div className="text-sm" style={{ color: "var(--c-muted2)" }}>Step {step + 1} of {STEPS.length} · {STEPS[step]}</div>
    </div>
  );
}

export function ReportDialog() {
  const { dialogOpen, spot, busy, error, justSent } = useReports();
  const { cancel, startPicking, pickSpot, submit } = useReports.getState();
  const sites = useStore((s) => s.sites);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Checklist>({});
  const [note, setNote] = useState("");
  const [when, setWhen] = useState(() => localInput(new Date()));
  const [locError, setLocError] = useState<string | null>(null);
  const photosEnabled = useCommunity((s) => s.photosEnabled);
  const [tidy, setTidy] = useState<Proofread | null>(null);   // the AI suggestion, until accepted or dismissed
  const [useTidy, setUseTidy] = useState(false);               // true once the person accepted it
  const [tidyBusy, setTidyBusy] = useState(false);
  const [tidyError, setTidyError] = useState<string | null>(null);
  const [photo, setPhoto] = useState<{ upload: PhotoUpload; preview: string } | null>(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const previewUrl = photo?.preview;
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  const linked = useMemo(() => (spot && sites ? nearestSite(spot, sites.sites) : null), [spot, sites]);

  if (!dialogOpen) return null;

  if (justSent) {
    const rewards = justSent.rewards;
    return (
      <Modal title="Thank you" onClose={cancel}>
        {rewards ? (
          <>
            <p className="mb-3" style={{ color: "var(--c-muted)" }}>
              Your report is on the map{justSent.site_id ? ` and on the page for site ${justSent.site_id}` : ""}. It is shown as
              unverified and does not change any testing priority.
            </p>
            <div className="rounded-lg px-4 py-3 mb-4" style={{ background: "var(--c-raised)", border: "1px solid var(--c-border-subtle)" }}>
              <div className="font-display text-2xl mb-1" style={{ fontWeight: 500 }}>
                {rewards.total > 0 ? `+${rewards.total} points` : "No points this time"}
              </div>
              <ul className="text-sm flex flex-col gap-0.5" style={{ color: "var(--c-muted)" }}>
                {rewards.lines.map((l) => (
                  <li key={l.reason}>{l.points > 0 ? `+${l.points} ` : ""}{l.label}</li>
                ))}
              </ul>
              {rewards.new_badges.length > 0 && (
                <p className="text-sm mt-2 font-medium" style={{ color: "var(--c-accent)" }}>
                  New badge{rewards.new_badges.length > 1 ? "s" : ""}: {rewards.new_badges.map((b) => b.title).join(", ")}
                </p>
              )}
            </div>
          </>
        ) : (
          <p className="mb-4" style={{ color: "var(--c-muted)" }}>
            Thank you. A moderator will look at your report before it is shown, and points are added once it is approved.
          </p>
        )}
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

  async function tidyNote() {
    setTidyBusy(true);
    setTidyError(null);
    try {
      setTidy(await proofreadNote(note.trim()));
      setUseTidy(false);
    } catch (e) {
      setTidyError(e instanceof Error ? e.message : "The note helper is not available. You can send your note as it is.");
    } finally {
      setTidyBusy(false);
    }
  }

  async function pickPhoto(file: File | undefined) {
    if (!file) return;
    setPhotoBusy(true);
    setPhotoError(null);
    try {
      const upload = await uploadPhoto(await shrinkImage(file));
      setPhoto({ upload, preview: URL.createObjectURL(file) });
    } catch (e) {
      setPhotoError(e instanceof Error ? e.message : "The photo could not be added. You can still send the report.");
    } finally {
      setPhotoBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function send() {
    const chosen = useTidy && tidy ? tidy.clean : null;
    const ok = await submit({
      observed_at: new Date(when).toISOString(),
      checklist: answers,
      note: note.trim(),
      note_clean: chosen && chosen !== note.trim() ? chosen : null,
      photo_id: photo?.upload.id ?? null,
    });
    if (ok) {
      setAnswers({});
      setNote("");
      setTidy(null);
      setUseTidy(false);
      setPhoto(null);
      setStep(0);
      setWhen(localInput(new Date()));
    }
  }

  const canNext = step === 0 ? spot !== null && when !== "" : step === 1 ? hasAnswers(answers) : true;
  const summary = describeChecklist(answers);

  return (
    <Modal title="Report what you see" size="lg" onClose={cancel}>
      <Progress step={step} />

      <div className="min-h-[19rem]">
        {step === 0 && (
          <div className="flex flex-col gap-5">
            <div>
              <div className="text-sm font-medium mb-1">Where are you?</div>
              <p className="text-sm mb-2.5" style={{ color: "var(--c-muted)" }}>
                {spot
                  ? linked
                    ? `Close to site ${linked.id} (about ${linked.metres} m away).`
                    : "Not near one of our sites. It will still show on the map."
                  : "Choose the spot where you are looking at the stream."}
              </p>
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
            <label className="block">
              <span className="block text-sm font-medium mb-1.5">When did you visit?</span>
              <input
                type="datetime-local"
                value={when}
                max={localInput(new Date())}
                onChange={(e) => setWhen(e.target.value)}
                className="px-3 py-2 rounded-lg text-base"
                style={{ background: "var(--c-canvas)", border: "1px solid var(--c-border)", color: "var(--c-text)" }}
              />
            </label>
          </div>
        )}

        {step === 1 && (
          <div>
            <p className="text-sm mb-3" style={{ color: "var(--c-muted2)" }}>Answer whatever you noticed. Skip the rest.</p>
            <div className="grid sm:grid-cols-2 gap-x-6 gap-y-3.5">
              {QUESTIONS.map((q) => (
                <fieldset key={q.key} className={q.key === "animals" ? "sm:col-span-2" : ""}>
                  <legend className="text-sm font-medium mb-1.5">{q.label}</legend>
                  <div className="flex flex-wrap gap-1.5">
                    {q.options.map((o) => {
                      const value = answers[q.key];
                      const selected = Array.isArray(value) ? value.includes(o.value) : value === o.value;
                      return <Chip key={o.value} selected={selected} onClick={() => choose(q.key, o.value, q.multi)}>{o.label}</Chip>;
                    })}
                  </div>
                </fieldset>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-4">
            <div className="rounded-lg px-4 py-3 text-sm" style={{ background: "var(--c-raised)", border: "1px solid var(--c-border-subtle)" }}>
              <div className="font-medium mb-1">
                {linked ? `Site ${linked.id}` : "Outside our sites"} · {new Date(when).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
              </div>
              <div style={{ color: "var(--c-muted)" }}>{summary.join(" · ")}</div>
            </div>
            <label className="block">
              <span className="block text-sm font-medium mb-1.5">Anything else? (optional)</span>
              <textarea
                value={note}
                onChange={(e) => { setNote(e.target.value); setTidy(null); setUseTidy(false); }}
                maxLength={NOTE_MAX}
                rows={3}
                className="w-full px-3 py-2 rounded-lg text-base resize-none"
                style={{ background: "var(--c-canvas)", border: "1px solid var(--c-border)", color: "var(--c-text)" }}
              />
              <span className="block text-sm mt-1" style={{ color: "var(--c-muted2)" }}>
                {note.length}/{NOTE_MAX}. No links or personal details, please.
              </span>
            </label>

            {note.trim() && !tidy && (
              <div>
                <button type="button" onClick={() => void tidyNote()} disabled={tidyBusy}
                        className="px-3 py-1.5 rounded-lg text-sm font-medium disabled:opacity-50" style={outlineButton}>
                  {tidyBusy ? "Checking…" : "Tidy my note with AI"}
                </button>
                {tidyError && <span className="text-sm ml-3" style={{ color: "var(--c-danger-text)" }}>{tidyError}</span>}
              </div>
            )}
            {tidy && (
              <div className="rounded-lg px-4 py-3 text-sm" style={{ background: "var(--c-raised)", border: "1px solid var(--c-border-subtle)" }}>
                {tidy.flags.includes("personal_info") && (
                  <p className="mb-2 font-medium" style={{ color: "var(--c-warn-text)" }}>
                    This looks like it has personal details (a name, email or phone number). Please remove them, or a moderator will review the report first.
                  </p>
                )}
                {tidy.flags.includes("accusation") && (
                  <p className="mb-2" style={{ color: "var(--c-warn-text)" }}>Please describe what you saw rather than blaming a named person or company.</p>
                )}
                {tidy.flags.includes("off_topic") && (
                  <p className="mb-2" style={{ color: "var(--c-warn-text)" }}>This note may not be about the stream.</p>
                )}
                {useTidy ? (
                  <>
                    <div className="mb-1" style={{ color: "var(--c-muted2)" }}>Using the suggested wording (your own words are kept too):</div>
                    <p className="mb-2 italic">“{tidy.clean}”</p>
                    <button type="button" onClick={() => setUseTidy(false)} className="px-3 py-1 rounded-lg font-medium" style={outlineButton}>
                      Use my own wording
                    </button>
                  </>
                ) : tidy.changed ? (
                  <>
                    <div className="mb-1" style={{ color: "var(--c-muted2)" }}>Suggested wording:</div>
                    <p className="mb-2 italic">“{tidy.clean}”</p>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => setUseTidy(true)} className="px-3 py-1 rounded-lg font-semibold" style={primaryButton}>Use this</button>
                      <button type="button" onClick={() => setTidy(null)} className="px-3 py-1 rounded-lg font-medium" style={outlineButton}>Keep mine</button>
                    </div>
                  </>
                ) : (
                  <p style={{ color: "var(--c-muted)" }}>Your note reads fine as it is.</p>
                )}
              </div>
            )}

            {photosEnabled && (
              <div>
                <div className="text-sm font-medium mb-1.5">Photo (optional)</div>
                <input ref={fileRef} type="file" accept="image/*" className="sr-only" id="report-photo"
                       onChange={(e) => void pickPhoto(e.target.files?.[0])} />
                {photo ? (
                  <div className="flex items-start gap-3">
                    <img src={photo.preview} alt="Your photo" className="w-24 h-24 object-cover rounded-lg" style={{ border: "1px solid var(--c-border)" }} />
                    <div className="text-sm">
                      <button type="button" onClick={() => setPhoto(null)} className="underline font-medium" style={{ color: "var(--c-accent)" }}>Remove photo</button>
                      {photoFlagMessage(photo.upload) && <p className="mt-1" style={{ color: "var(--c-warn-text)" }}>{photoFlagMessage(photo.upload)}</p>}
                    </div>
                  </div>
                ) : (
                  <label htmlFor="report-photo" className="inline-block px-3 py-1.5 rounded-lg text-sm font-medium cursor-pointer"
                         style={{ ...outlineButton, opacity: photoBusy ? 0.5 : 1 }}>
                    {photoBusy ? "Checking the photo…" : "Add a photo"}
                  </label>
                )}
                {photoError && <p className="text-sm mt-1.5" style={{ color: "var(--c-danger-text)" }}>{photoError}</p>}
                <p className="text-sm mt-1.5" style={{ color: "var(--c-muted2)" }}>
                  Please do not photograph people or number plates. Location data is removed from your photo.
                </p>
              </div>
            )}
            <p className="text-sm" style={{ color: "var(--c-muted2)" }}>
              Your nickname will show next to the report. Reports are unverified and never change a testing priority.{" "}
              <button type="button" onClick={() => useCommunity.getState().openPrivacy()} className="underline" style={{ color: "var(--c-accent)" }}>
                How we use your data
              </button>
            </p>
          </div>
        )}
      </div>

      <ErrorLine message={error} />
      <div className="flex gap-3 mt-4 pt-4" style={{ borderTop: "1px solid var(--c-border-subtle)" }}>
        {step === 0 ? (
          <button type="button" onClick={cancel} className="px-4 py-2.5 rounded-lg font-medium" style={outlineButton}>Cancel</button>
        ) : (
          <button type="button" onClick={() => setStep(step - 1)} className="px-4 py-2.5 rounded-lg font-medium" style={outlineButton}>Back</button>
        )}
        {step < STEPS.length - 1 ? (
          <button
            type="button"
            disabled={!canNext}
            onClick={() => setStep(step + 1)}
            className="flex-1 px-4 py-2.5 rounded-lg font-semibold disabled:opacity-50"
            style={primaryButton}
          >
            Next
          </button>
        ) : (
          <button
            type="button"
            disabled={busy || !spot || !hasAnswers(answers)}
            onClick={() => void send()}
            className="flex-1 px-4 py-2.5 rounded-lg font-semibold disabled:opacity-50"
            style={primaryButton}
          >
            {busy ? "Sending…" : "Send report"}
          </button>
        )}
      </div>
    </Modal>
  );
}
