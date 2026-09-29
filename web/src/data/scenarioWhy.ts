/**
 * Explanations for the What-if tab: why a change moves the testing priority, and why the
 * same change gives different results at different places. Pure functions so they can be
 * tested. Wording follows the project rules: never a probability, never safe/unsafe.
 */
import { TIER_LABEL, tierOf } from "./copy";

export interface Multipliers {
  lambda: number;
  Q: number;
  C: number;
}

export interface Outcome {
  score: number;
  n: number;
}

const fmt = (x: number): string => String(Number(x.toFixed(2)));

/** One sentence per changed setting, saying which way it pushes the medicine level and why. */
export function effectSentences(m: Multipliers, citizen: boolean): string[] {
  const out: string[] = [];
  if (m.lambda < 1) {
    out.push(citizen
      ? "Less untreated wastewater leaks into the stream, so less medicine reaches it."
      : `λ × ${fmt(m.lambda)}: less untreated leakage, so less drug load reaches the stream and PEC falls in proportion.`);
  } else if (m.lambda > 1) {
    out.push(citizen
      ? "More untreated wastewater leaks into the stream, so more medicine reaches it."
      : `λ × ${fmt(m.lambda)}: more untreated leakage, so more drug load reaches the stream and PEC rises in proportion.`);
  }
  if (m.Q < 1) {
    out.push(citizen
      ? "The stream carries less water, so the same amount of medicine is diluted less and the level goes up."
      : `Q × ${fmt(m.Q)}: lower flow means less dilution, so PEC rises in inverse proportion.`);
  } else if (m.Q > 1) {
    out.push(citizen
      ? "The stream carries more water, so the medicine is diluted more and the level goes down."
      : `Q × ${fmt(m.Q)}: higher flow means more dilution, so PEC falls in inverse proportion.`);
  }
  if (m.C < 1) {
    out.push(citizen
      ? "People use less of this medicine, so less of it ends up in wastewater."
      : `Consumption × ${fmt(m.C)}: less drug used, so the load, and PEC, fall in proportion.`);
  } else if (m.C > 1) {
    out.push(citizen
      ? "People use more of this medicine, so more of it ends up in wastewater."
      : `Consumption × ${fmt(m.C)}: more drug used, so the load, and PEC, rise in proportion.`);
  }
  return out;
}

/** Overall factor applied to every simulated RQ: λ × C / Q. */
export function combinedFactor(m: Multipliers): number {
  return (m.lambda * m.C) / m.Q;
}

/**
 * Explains what happened at this particular site and medicine: crossed a group line,
 * moved within a group, or was too far from the line to move a group.
 */
export function outcomeSentence(base: Outcome, scen: Outcome, citizen: boolean): string {
  const from = tierOf(base.score);
  const to = tierOf(scen.score);
  const delta = scen.score - base.score;

  if (from !== to) {
    return citizen
      ? `This change was big enough to move this spot from ${TIER_LABEL[from].toLowerCase()} to ${TIER_LABEL[to].toLowerCase()}. It started close enough to the line between the two groups to cross it.`
      : `The score moved from ${base.score.toFixed(3)} to ${scen.score.toFixed(3)}, crossing the ${to === "high" || from === "high" ? "0.5" : "0.1"} threshold between ${from} and ${to}.`;
  }
  if (Math.abs(delta) < 0.005) {
    if (from === "high" && base.score >= 0.9) {
      return citizen
        ? "For this spot and medicine, this change makes almost no difference. It already sits well above the level of concern in nearly every simulated situation, so there is little left to move."
        : `The score is essentially unchanged (Δ ${delta >= 0 ? "+" : ""}${delta.toFixed(3)}). Nearly all draws are already above RQ = 1 (score ${base.score.toFixed(3)}), so the score is saturated.`;
    }
    if (from === "low" && base.score <= 0.03) {
      return citizen
        ? "For this spot and medicine, this change makes almost no difference. It sits well below the level of concern in nearly every simulated situation, so a change of this size cannot lift it."
        : `The score is essentially unchanged (Δ ${delta >= 0 ? "+" : ""}${delta.toFixed(3)}). Nearly all draws are still below RQ = 1 (score ${base.score.toFixed(3)}).`;
    }
    return citizen
      ? "For this spot and medicine, this change makes almost no difference."
      : `The score is essentially unchanged (Δ ${delta >= 0 ? "+" : ""}${delta.toFixed(3)}).`;
  }
  if (from === "high" && base.score >= 0.9) {
    return citizen
      ? "This spot starts well above the level of concern in almost every simulated situation, so a change of this size nudges it but cannot lower its group."
      : `Most draws start far above RQ = 1 (score ${base.score.toFixed(3)}), so this factor shifts few of them below 1 and the tier does not change.`;
  }
  if (from === "low" && base.score <= 0.03) {
    return citizen
      ? "This spot starts well below the level of concern in almost every simulated situation, so a change of this size cannot lift its group."
      : `Almost all draws start well below RQ = 1 (score ${base.score.toFixed(3)}), so this factor lifts few of them above 1 and the tier does not change.`;
  }
  return citizen
    ? "The ranking moved, but not far enough to cross into a different group."
    : `The score moved by ${delta >= 0 ? "+" : ""}${delta.toFixed(3)} but stayed within the ${from} tier.`;
}

/** Expert detail: how many simulated draws crossed RQ = 1, and by what overall factor. */
export function crossingDetail(base: Outcome, scen: Outcome, m: Multipliers): string {
  const net = Math.round((scen.score - base.score) * scen.n);
  const direction = net >= 0 ? "moved above" : "moved below";
  return `Overall factor λ × C / Q = ${fmt(combinedFactor(m))}. ${Math.abs(net)} of ${scen.n} stored draws ${direction} RQ = 1.`;
}

/** Why the same change gives different results from place to place. */
export function whyDiffers(citizen: boolean): string {
  return citizen
    ? "Every place and medicine starts from a different level, depending on how many people live nearby, how much of the medicine is used and how big the stream is. The same change moves each one by a different amount, and a group only changes when a place crosses the line between groups."
    : "Each site × drug starts with a different distribution of RQ draws (different population, consumption and flow priors). The same multiplier shifts every draw by the same factor, but the score only changes for draws that cross RQ = 1, and the tier only changes when the score crosses 0.1 or 0.5.";
}
