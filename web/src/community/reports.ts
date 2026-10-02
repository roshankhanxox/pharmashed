/** Citizen reports (S5 phase 2): the checklist questions, plain-language answers, and API calls. */
import { apiFetch } from "./api";
import type { Rewards } from "./points";

export type Checklist = Record<string, string | string[]>;

export interface Report {
  id: string;
  lat: number;
  lon: number;
  site_id: string | null;
  city: string | null;
  observed_at: string;
  checklist: Checklist;
  note: string;
  is_sample: boolean;
  author: string;
  mine: boolean;
  /** Path (relative to the API base) of the photo, when there is an approved one. */
  photo_url?: string | null;
  /** Only on the response to filing a report. */
  rewards?: Rewards | null;
  /** Only on the person's own reports. */
  status?: "pending" | "approved" | "hidden";
}

export interface Question {
  key: string;
  label: string;
  multi?: boolean;
  options: { value: string; label: string }[];
}

/** Must match CHECKLIST in api/src/pharmashed_api/community/reports.py. */
export const QUESTIONS: Question[] = [
  { key: "water_colour", label: "Water colour", options: [
    { value: "clear", label: "Clear" }, { value: "cloudy", label: "Cloudy" }, { value: "brown", label: "Brown" },
    { value: "green", label: "Green" }, { value: "grey", label: "Grey" }] },
  { key: "smell", label: "Smell", options: [
    { value: "none", label: "None" }, { value: "earthy", label: "Earthy" }, { value: "musty", label: "Musty" },
    { value: "sewage", label: "Sewage" }, { value: "chemical", label: "Chemical" }] },
  { key: "foam", label: "Foam on the water", options: [
    { value: "none", label: "None" }, { value: "light", label: "A little" }, { value: "heavy", label: "A lot" }] },
  { key: "litter", label: "Litter", options: [
    { value: "none", label: "None" }, { value: "some", label: "Some" }, { value: "a_lot", label: "A lot" }] },
  { key: "animals", label: "Animals you saw", multi: true, options: [
    { value: "fish", label: "Fish" }, { value: "birds", label: "Birds" }, { value: "insects", label: "Insects" },
    { value: "frogs", label: "Frogs" }, { value: "none_seen", label: "None seen" }] },
  { key: "flow", label: "How is it flowing?", options: [
    { value: "dry", label: "Dry" }, { value: "trickle", label: "A trickle" }, { value: "normal", label: "Normal" },
    { value: "high", label: "High" }] },
  { key: "rain_24h", label: "Rain in the last 24 hours", options: [
    { value: "none", label: "None" }, { value: "light", label: "Light" }, { value: "heavy", label: "Heavy" }] },
];

export const NOTE_MAX = 500;

/** [question, answer] pairs for the answered questions, in question order. */
export function checklistPairs(checklist: Checklist): [string, string][] {
  const pairs: [string, string][] = [];
  for (const q of QUESTIONS) {
    const value = checklist[q.key];
    if (value === undefined || value === "" || (Array.isArray(value) && value.length === 0)) continue;
    const label = (v: string) => q.options.find((o) => o.value === v)?.label ?? v;
    pairs.push([q.label, Array.isArray(value) ? value.map(label).join(", ") : label(value)]);
  }
  return pairs;
}

/** "Water colour: Cloudy" style lines for the answered questions, in question order. */
export function describeChecklist(checklist: Checklist): string[] {
  return checklistPairs(checklist).map(([q, a]) => `${q}: ${a}`);
}

/** Same rule as the server: at least one answered question. */
export function hasAnswers(checklist: Checklist): boolean {
  return Object.values(checklist).some((v) => (Array.isArray(v) ? v.length > 0 : v !== ""));
}

/** "3 days ago", "today": coarse on purpose. */
export function ago(iso: string, now: Date = new Date()): string {
  const days = Math.floor((now.getTime() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

/** Public read. When signed in, the token marks the person's own reports (`mine`). */
export const fetchReports = (signedIn: boolean) => apiFetch<Report[]>("/reports?limit=500", { auth: signedIn });

export interface ReportInput {
  lat: number;
  lon: number;
  observed_at: string;
  checklist: Checklist;
  note: string;
  /** The AI-tidied note the person chose to use (the original stays in `note`). */
  note_clean?: string | null;
  photo_id?: string | null;
}

export interface Proofread {
  original: string;
  clean: string;
  changed: boolean;
  flags: ("personal_info" | "accusation" | "off_topic")[];
}

export interface PhotoUpload {
  id: string;
  ai_ok: boolean | null;
  flags: Record<string, boolean>;
}

export const proofreadNote = (note: string) =>
  apiFetch<Proofread>("/ai/proofread", { method: "POST", auth: true, body: JSON.stringify({ note }) });

export function uploadPhoto(file: Blob): Promise<PhotoUpload> {
  const form = new FormData();
  form.append("file", file, "photo.jpg");
  return apiFetch<PhotoUpload>("/photos", { method: "POST", auth: true, body: form });
}

/** Shrinks a photo to at most `edge` pixels on its long side as a JPEG, so phone photos upload quickly.
 * Falls back to the original file if the browser cannot decode it (the server accepts and re-checks it). */
export async function shrinkImage(file: File, edge = 1600): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const scale = Math.min(1, edge / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    return blob ?? file;
  } catch {
    return file;
  }
}

/** Plain-language reasons shown when the photo check flagged something. */
export function photoFlagMessage(upload: PhotoUpload): string | null {
  if (upload.ai_ok === true) return null;
  if (upload.ai_ok === null) return "We could not check this photo automatically, so a moderator will look at it before it is shown.";
  const f = upload.flags;
  const why = [f.people && "a person", f.plate && "a number plate", f.not_a_stream && "something other than a stream"].filter(Boolean);
  return `This photo may show ${why.join(" and ")}, so a moderator will look at it before it is shown.`;
}

export const postReport = (input: ReportInput) =>
  apiFetch<Report>("/reports", { method: "POST", auth: true, body: JSON.stringify(input) });

/** Great-circle distance in metres. */
export function distanceM(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const rad = Math.PI / 180;
  const dphi = (b.lat - a.lat) * rad;
  const dl = (b.lon - a.lon) * rad;
  const h = Math.sin(dphi / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dl / 2) ** 2;
  return 2 * 6_371_000 * Math.asin(Math.sqrt(h));
}

/** The site a pin would be linked to (within 1 km, like the server), for instant feedback in the form. */
export function nearestSite(
  spot: { lat: number; lon: number },
  sites: { id: string; lonlat: [number, number] }[],
): { id: string; metres: number } | null {
  let best: { id: string; metres: number } | null = null;
  for (const s of sites) {
    const metres = distanceM(spot, { lat: s.lonlat[1], lon: s.lonlat[0] });
    if (!best || metres < best.metres) best = { id: s.id, metres };
  }
  return best && best.metres <= 1000 ? { id: best.id, metres: Math.round(best.metres) } : null;
}

export const flagReport = (id: string, reason: string) =>
  apiFetch<{ flagged: boolean; held: boolean }>(`/reports/${id}/flag`, { method: "POST", auth: true, body: JSON.stringify({ reason }) });
