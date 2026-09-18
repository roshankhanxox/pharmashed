/**
 * Client-side scenario recompute (M20).
 * Mirrors A4 / M16: RQ' = RQ * mλ * mC / mQ
 * Only valid for w=0 sites (all illustrative sites are w=0).
 */

export interface ScenarioResult {
  score: number;
  p5: number;
  p50: number;
  p95: number;
  n: number;
}

export interface ScenarioMultipliers {
  lambda?: number;
  Q?: number;
  C?: number;
}

function quantile(arr: Float32Array, q: number): number {
  if (arr.length === 0) return 0;
  const sorted = Float32Array.from(arr).sort();
  const idx = q * (sorted.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

export function applyScenario(
  stored: Float32Array,
  m: ScenarioMultipliers,
): ScenarioResult {
  const mLambda = m.lambda ?? 1;
  const mQ = m.Q ?? 1;
  const mC = m.C ?? 1;
  const f = (mLambda * mC) / mQ;

  let exceed = 0;
  const scaled = new Float32Array(stored.length);
  for (let i = 0; i < stored.length; i++) {
    const v = stored[i] * f;
    scaled[i] = v;
    if (v > 1) exceed++;
  }

  return {
    score: stored.length > 0 ? exceed / stored.length : 0,
    p5: quantile(scaled, 0.05),
    p50: quantile(scaled, 0.5),
    p95: quantile(scaled, 0.95),
    n: stored.length,
  };
}
