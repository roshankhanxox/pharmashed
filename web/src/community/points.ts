/** Points, badges and the leaderboard (S5 phase 4): types, API calls and small display helpers. */
import { apiFetch } from "./api";
import type { Report } from "./reports";

export interface RewardLine {
  reason: string;
  label: string;
  points: number;
}

/** Returned with a new report: what it earned (null while it waits for review). */
export interface Rewards {
  lines: RewardLine[];
  total: number;
  new_badges: { key: string; title: string }[];
}

export interface Badge {
  key: string;
  title: string;
  description: string;
  earned: boolean;
  awarded_at: string | null;
}

export interface Challenge {
  key: string;
  title: string;
  description: string;
  week: string;
}

export interface Progress {
  points: number;
  points_this_week: number;
  rank: number | null;
  streak_weeks: number;
  badges: Badge[];
  challenge: Challenge & { done: boolean };
  recent: (RewardLine & { created_at: string; site_id: string | null; reversed: boolean })[];
}

export interface BoardEntry {
  rank: number;
  nickname: string;
  points: number;
  reports: number;
  badges: number;
  is_me: boolean;
}

export interface Board {
  scope: BoardScope;
  city: string | null;
  entries: BoardEntry[];
  me: { rank: number; points: number; listed: boolean } | null;
}

export type BoardScope = "all" | "week" | "month";

export const SCOPE_LABEL: Record<BoardScope, string> = { all: "All time", week: "This week", month: "Last 30 days" };

export const fetchProgress = () => apiFetch<Progress>("/me/progress", { auth: true });
export const fetchMyReports = () => apiFetch<Report[]>("/me/reports", { auth: true });
export const fetchChallenge = () => apiFetch<Challenge>("/challenge");

export function fetchBoard(scope: BoardScope, city: string | null, signedIn: boolean): Promise<Board> {
  const q = new URLSearchParams({ scope });
  if (city) q.set("city", city);
  return apiFetch<Board>(`/leaderboard?${q}`, { auth: signedIn });
}

/** "+10" / "-10" / "0". */
export const signed = (n: number): string => (n > 0 ? `+${n}` : String(n));

/** Plain-language name for a report's review status (author's own view). */
export const STATUS_LABEL: Record<string, string> = {
  approved: "Public",
  pending: "Waiting for review",
  hidden: "Hidden by a moderator",
};

/** The rules, in the order people meet them. Shown on the leaderboard page. */
export const HOW_POINTS_WORK: string[] = [
  "+10 for each approved report near one of our sites",
  "+5 when your photo passes the check",
  "+5 for your first report at a site",
  "+10 for a site nobody had reported in the last 30 days",
  "+5 per extra week in a row you report, up to +20",
  "+20 for finishing the weekly challenge",
  "At most 3 rewarded reports a day, and one per site per week. Extra reports are still shown, they just earn nothing.",
  "Reports far from our sites are shown on the map but earn no points. A report a moderator hides loses its points.",
];
