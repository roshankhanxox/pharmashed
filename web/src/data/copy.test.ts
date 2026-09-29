import { describe, expect, it } from "vitest";
import {
  CITIZEN_TAB_LABEL, DEMO_NOTICE, DRUG_USE, SCORE_CAVEAT, TIER_LABEL, TIER_LEGEND,
  TIER_SENTENCE, scenarioSentence, tierOf,
} from "./copy";

const ALL_COPY = [
  ...Object.values(TIER_LABEL), ...Object.values(TIER_LEGEND), ...Object.values(TIER_SENTENCE),
  ...Object.values(DRUG_USE), ...Object.values(CITIZEN_TAB_LABEL), SCORE_CAVEAT, DEMO_NOTICE,
  scenarioSentence("high", "low"), scenarioSentence("low", "low"),
  scenarioSentence("high", "high", -0.1), scenarioSentence("high", "high", 0.1),
];

describe("citizen copy", () => {
  it("never calls a stream safe/unsafe or the score a probability", () => {
    for (const text of ALL_COPY) {
      expect(text as string).not.toMatch(/\b(unsafe|safe|dangerous|probab\w*|chance|risk of)\b/i);
    }
  });

  it("uses the same tier thresholds as the model (high >= 0.5, medium >= 0.1)", () => {
    expect(tierOf(0.5)).toBe("high");
    expect(tierOf(0.49)).toBe("medium");
    expect(tierOf(0.1)).toBe("medium");
    expect(tierOf(0.09)).toBe("low");
  });

  it("describes tier changes in words", () => {
    expect(scenarioSentence("high", "medium")).toContain("from high priority to medium priority");
  });

  it("notes movement inside an unchanged tier", () => {
    expect(scenarioSentence("high", "high", -0.14)).toBe("Testing priority would stay high priority, though a little lower.");
    expect(scenarioSentence("high", "high", 0)).toBe("Testing priority would stay high priority.");
  });
});
