/**
 * Plain-language wording for citizen view.
 *
 * Rules from the project brief: the sampling priority score is never called a probability,
 * and no stream is ever called safe or unsafe. copy.test.ts enforces both for every string here.
 */
import type { Tab } from "./store";

export type Tier = "high" | "medium" | "low";

/** Short label for a testing-priority tier. */
export const TIER_LABEL: Record<Tier, string> = {
  high: "High priority",
  medium: "Medium priority",
  low: "Lower priority",
};

/** Map legend wording, matched to the tier colours. */
export const TIER_LEGEND: Record<Tier, string> = {
  high: "Test soon",
  medium: "Worth testing",
  low: "Lower priority",
};

/** One-sentence explanation of what a tier means for a site. */
export const TIER_SENTENCE: Record<Tier, string> = {
  high: "This spot is among the best places to collect a water sample first. A test here would tell us the most.",
  medium: "This spot is worth testing, after the high-priority ones.",
  low: "This spot is a lower priority for testing right now.",
};

/** What each medicine is commonly used for (general knowledge, not a sourced figure). */
export const DRUG_USE: Record<string, string> = {
  carbamazepine: "epilepsy medicine",
  atenolol: "blood pressure medicine",
  losartan: "blood pressure medicine",
  irbesartan: "blood pressure medicine",
  paracetamol: "pain and fever relief",
  citalopram: "antidepressant",
};

/** Tab names in citizen view. Expert-only tabs are not listed. */
export const CITIZEN_TAB_LABEL: Partial<Record<Tab, string>> = {
  home: "Home",
  explore: "Stream map",
  scenarios: "What if?",
  leaderboard: "Leaderboard",
  mine: "My streams",
  moderation: "Moderation",
};

/** Explains the score in words, always with the required caveat. */
export const SCORE_CAVEAT =
  "This is a way to decide where to test first. It is not a measurement of the water and not a verdict on any stream.";

/** Placeholder-data notice shown in citizen view. */
export const DEMO_NOTICE = "Demo data: the drug numbers behind this prototype are placeholders, not measurements.";

/**
 * Turns a tier change into a sentence for the what-if view. When the tier stays the same,
 * `delta` (scenario score minus baseline score) says whether it moved within the tier.
 */
export function scenarioSentence(from: Tier, to: Tier, delta = 0): string {
  if (from !== to) {
    return `Testing priority would change from ${TIER_LABEL[from].toLowerCase()} to ${TIER_LABEL[to].toLowerCase()}.`;
  }
  const stay = `Testing priority would stay ${TIER_LABEL[from].toLowerCase()}`;
  if (delta <= -0.005) return `${stay}, though a little lower.`;
  if (delta >= 0.005) return `${stay}, though a little higher.`;
  return `${stay}.`;
}

/** Maps a sampling priority score to its tier (high ≥ 0.5, medium ≥ 0.1). */
export function tierOf(score: number): Tier {
  if (score >= 0.5) return "high";
  if (score >= 0.1) return "medium";
  return "low";
}
