/**
 * C1 check: predicted LOD share vs observed detection frequency scatter.
 */

export interface ScatterPoint {
  x: number;
  y: number;
  label?: string;
}

interface ScatterProps {
  points: ScatterPoint[];
  rho?: number;
  n?: number;
  xLabel?: string;
  yLabel?: string;
}

const W = 260;
const H = 200;
const PAD = { top: 20, right: 20, bottom: 40, left: 40 };
const IW = W - PAD.left - PAD.right;
const IH = H - PAD.top - PAD.bottom;

function scale(vals: number[]): (v: number) => number {
  const min = Math.min(...vals, 0);
  const max = Math.max(...vals, 1);
  return (v) => ((v - min) / (max - min)) * IH;
}

export function Scatter({ points, rho, n, xLabel = "Predicted", yLabel = "Observed" }: ScatterProps) {
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const scaleX = (v: number) => ((v - Math.min(...xs, 0)) / (Math.max(...xs, 1) - Math.min(...xs, 0))) * IW;
  const scaleY = scale(ys);

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-full max-w-full" role="img">
      <title>Scatter: {xLabel} vs {yLabel}</title>
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {/* axes */}
        <line x1={0} y1={IH} x2={IW} y2={IH} stroke="#ccc" />
        <line x1={0} y1={0} x2={0} y2={IH} stroke="#ccc" />

        {/* points */}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={scaleX(p.x)} cy={IH - scaleY(p.y)} r={4} fill="var(--c-accent)" opacity={0.7} />
            {p.label && (
              <text x={scaleX(p.x) + 6} y={IH - scaleY(p.y) + 3} fontSize={12} fill="#555">
                {p.label}
              </text>
            )}
          </g>
        ))}

        {/* ρ, n */}
        {rho != null && (
          <text x={IW} y={10} textAnchor="end" fontSize={12} fill="var(--c-accent)">
            ρ = {rho.toFixed(2)}{n != null ? `, n = ${n}` : ""}
          </text>
        )}

        {/* axis labels */}
        <text x={IW / 2} y={IH + 30} textAnchor="middle" fontSize={12} fill="#888">{xLabel}</text>
        <text
          x={-(IH / 2)}
          y={-28}
          textAnchor="middle"
          fontSize={12}
          fill="#888"
          transform="rotate(-90)"
        >{yLabel}</text>
      </g>
    </svg>
  );
}
