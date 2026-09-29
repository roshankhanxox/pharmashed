import { describe, expect, it } from "vitest";
import { combinedFactor, crossingDetail, effectSentences, outcomeSentence, whyDiffers } from "./scenarioWhy";

const NONE = { lambda: 1, Q: 1, C: 1 };

describe("scenario explanations", () => {
  it("explains each changed setting and stays silent for unchanged ones", () => {
    expect(effectSentences(NONE, true)).toEqual([]);
    expect(effectSentences({ ...NONE, lambda: 0.5 }, true)).toHaveLength(1);
    expect(effectSentences({ lambda: 3, Q: 0.2, C: 1 }, true)).toHaveLength(2);
  });

  it("combines multipliers as lambda * C / Q", () => {
    expect(combinedFactor({ lambda: 0.5, Q: 1, C: 1 })).toBe(0.5);
    expect(combinedFactor({ lambda: 1, Q: 0.2, C: 1 })).toBeCloseTo(5);
  });

  it("says why a saturated site does not change tier", () => {
    const text = outcomeSentence({ score: 1, n: 1000 }, { score: 0.86, n: 1000 }, true);
    expect(text).toMatch(/cannot lower its group/);
  });

  it("explains why an unchanged saturated score did not move", () => {
    const text = outcomeSentence({ score: 1, n: 1000 }, { score: 1, n: 1000 }, true);
    expect(text).toMatch(/little left to move/);
    expect(outcomeSentence({ score: 1, n: 1000 }, { score: 1, n: 1000 }, false)).toMatch(/saturated/);
  });

  it("says a tier crossing happened", () => {
    const text = outcomeSentence({ score: 0.55, n: 1000 }, { score: 0.3, n: 1000 }, true);
    expect(text).toMatch(/from high priority to medium priority/);
  });

  it("counts draws that crossed RQ = 1", () => {
    const text = crossingDetail({ score: 1, n: 200 }, { score: 0.86, n: 200 }, { lambda: 0.5, Q: 1, C: 1 });
    expect(text).toContain("28 of 200");
    expect(text).toContain("moved below");
  });

  it("never calls the score a probability or a stream safe/unsafe, in either voice", () => {
    const texts = [
      whyDiffers(true), whyDiffers(false),
      ...effectSentences({ lambda: 3, Q: 0.2, C: 2 }, true), ...effectSentences({ lambda: 0.5, Q: 5, C: 0.5 }, false),
      outcomeSentence({ score: 1, n: 10 }, { score: 0.9, n: 10 }, true), outcomeSentence({ score: 0.01, n: 10 }, { score: 0.02, n: 10 }, true),
      outcomeSentence({ score: 0.3, n: 10 }, { score: 0.3, n: 10 }, true), outcomeSentence({ score: 0.3, n: 10 }, { score: 0.35, n: 10 }, false),
    ];
    for (const t of texts) expect(t).not.toMatch(/\b(unsafe|safe|dangerous|probab\w*|chance)\b/i);
  });
});
