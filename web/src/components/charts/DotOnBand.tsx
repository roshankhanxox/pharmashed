/**
 * C4 check: observed max as a dot over the predicted [min_p5, max_p95] band on log axis.
 */

export interface DotOnBandProps {
  minP5: number;
  maxP95: number;
  observedMax: number;
  drug?: string;
}

const W = 300;
const H = 60;
const PAD = { left: 40, right: 20, top: 15, bottom: 25 };
const IW = W - PAD.left - PAD.right;
const IH = H - PAD.top - PAD.bottom;
const LOG_MIN = -2;
const LOG_MAX = 5;

function toX(val: number): number {
  if (val <= 0) return 0;
  const log = Math.log10(val);
  return ((log - LOG_MIN) / (LOG_MAX - LOG_MIN)) * IW;
}

export function DotOnBand({ minP5, maxP95, observedMax, drug }: DotOnBandProps) {
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-full max-w-full" role="img">
      <title>Observed vs predicted band{drug ? ` for ${drug}` : ""}</title>
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {/* band */}
        <rect
          x={toX(minP5)}
          y={IH / 4}
          width={Math.max(1, toX(maxP95) - toX(minP5))}
          height={IH / 2}
          fill="#60a5fa"
          opacity={0.4}
          rx={3}
        />
        {/* observed dot */}
        <circle cx={toX(observedMax)} cy={IH / 2} r={5} fill="#ef4444" />
        <text x={toX(observedMax)} y={IH / 2 - 8} textAnchor="middle" fontSize={8} fill="#ef4444">
          obs
        </text>

        {/* axis */}
        <line x1={0} y1={IH} x2={IW} y2={IH} stroke="#ccc" />
        {[LOG_MIN, 0, LOG_MAX].map((t) => {
          const x = toX(Math.pow(10, t));
          return (
            <g key={t}>
              <line x1={x} y1={IH} x2={x} y2={IH + 3} stroke="#aaa" />
              <text x={x} y={IH + 12} textAnchor="middle" fontSize={7} fill="#888">
                {t === 0 ? "1" : `10^${t}`}
              </text>
            </g>
          );
        })}
        <text x={IW / 2} y={IH + 22} textAnchor="middle" fontSize={8} fill="#888">
          ng/L (log scale)
        </text>
      </g>
    </svg>
  );
}
