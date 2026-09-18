import { describe, expect, it } from "vitest";
import { applyScenario } from "./scenario";

function makeDraws(values: number[]): Float32Array {
  return Float32Array.from(values);
}

describe("applyScenario", () => {
  it("identity multipliers preserve score", () => {
    const draws = makeDraws([0.5, 1.5, 0.8, 2.0, 0.3]);
    const result = applyScenario(draws, { lambda: 1, Q: 1, C: 1 });
    const expected = applyScenario(draws, {});
    expect(result.score).toBeCloseTo(expected.score, 5);
  });

  it("lambda × 2 doubles RQ, increases score", () => {
    // draws all below 0.5 → baseline score = 0
    const draws = makeDraws([0.3, 0.4, 0.2, 0.1, 0.45]);
    const base = applyScenario(draws, {});
    expect(base.score).toBe(0);
    // lambda × 10 → all above 1
    const high = applyScenario(draws, { lambda: 10 });
    expect(high.score).toBe(1);
  });

  it("Q × 2 halves RQ, reduces score", () => {
    // draws all above 1
    const draws = makeDraws([1.5, 2.0, 3.0]);
    const base = applyScenario(draws, {});
    expect(base.score).toBe(1);
    // Q × 10 → all below 1
    const low = applyScenario(draws, { Q: 10 });
    expect(low.score).toBe(0);
  });

  it("empty draws returns zero score", () => {
    const result = applyScenario(new Float32Array(0), {});
    expect(result.score).toBe(0);
  });

  it("returns p5, p50, p95", () => {
    const draws = makeDraws([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    const result = applyScenario(draws, {});
    expect(result.p5).toBeLessThan(result.p50);
    expect(result.p50).toBeLessThan(result.p95);
  });

  it("formula mλ * mC / mQ applied correctly", () => {
    const draws = makeDraws([1.0]);
    // f = 2 * 1.5 / 3 = 1.0 → RQ stays 1, NOT > 1
    const result = applyScenario(draws, { lambda: 2, C: 1.5, Q: 3 });
    expect(result.score).toBe(0);
  });
});
