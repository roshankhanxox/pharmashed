/**
 * Horizontal signed bar chart for Spearman rank correlations (drivers).
 */

export interface DriverEntry {
  param: string;
  rho: number;
}

interface TornadoProps {
  drivers: DriverEntry[];
  driverSentence?: string;
}

const W = 320;
const ROW_H = 22;
const LABEL_W = 95;
const CHART_W = W - LABEL_W - 20;
const MID = LABEL_W + CHART_W / 2;

export function Tornado({ drivers, driverSentence }: TornadoProps) {
  const h = drivers.length * ROW_H + 30;
  const sorted = [...drivers].sort((a, b) => Math.abs(b.rho) - Math.abs(a.rho));

  return (
    <div>
      <svg width={W} height={h} viewBox={`0 0 ${W} ${h}`} className="w-full max-w-full" role="img">
        <title>Sensitivity tornado — Spearman rank correlations</title>
        {/* center axis */}
        <line x1={MID} y1={0} x2={MID} y2={h - 20} stroke="#ccc" strokeWidth={1} />
        {sorted.map((d, i) => {
          const bw = (Math.abs(d.rho) / 1) * (CHART_W / 2);
          const x = d.rho >= 0 ? MID : MID - bw;
          const fill = d.rho >= 0 ? "var(--c-blue)" : "var(--c-danger-text)";
          const y = i * ROW_H + 4;
          return (
            <g key={d.param}>
              <rect x={x} y={y} width={bw} height={14} fill={fill} opacity={0.7} rx={2} />
              <text x={LABEL_W - 4} y={y + 10} textAnchor="end" fontSize={12} fill="#555">
                {d.param}
              </text>
              <text
                x={d.rho >= 0 ? x + bw + 4 : x - 4}
                y={y + 10}
                textAnchor={d.rho >= 0 ? "start" : "end"}
                fontSize={12}
                fill="#777"
              >
                {d.rho > 0 ? "+" : ""}{d.rho.toFixed(2)}
              </text>
            </g>
          );
        })}
        <text x={MID} y={h - 5} textAnchor="middle" fontSize={12} fill="#888">
          ρ (Spearman)
        </text>
      </svg>
      {driverSentence && (
        <p className="text-xs text-neutral-500 mt-1 italic">{driverSentence}</p>
      )}
    </div>
  );
}
