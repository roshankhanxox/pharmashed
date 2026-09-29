/**
 * One row per drug, log10 x-axis in ng/L.
 * Shows p5-p95 band, p50 tick, PNEC dashed line, LOD dashed line.
 */

import { InfoButton } from "../provenance/InfoButton";
import { Term } from "../glossary/Term";

export interface BandRow {
  drug: string;
  p5: number;
  p50: number;
  p95: number;
  pnec: number;
  lod: number | null;
  score: number;
  tier: "high" | "medium" | "low";
  pnecProvKey?: string;
  lodProvKey?: string;
}

interface BandChartProps {
  rows: BandRow[];
  onRowClick?: (drug: string) => void;
  expandedDrug?: string | null;
  ghostRows?: BandRow[];
}

const TIER_FILL: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

const W = 560;
const ROW_H = 28;
const LABEL_W = 110;
const CHART_W = W - LABEL_W - 40;
const LOG_MIN = -1;
const LOG_MAX = 5;

function toX(val: number): number {
  if (val <= 0) return 0;
  const log = Math.log10(val);
  return Math.max(0, Math.min(CHART_W, ((log - LOG_MIN) / (LOG_MAX - LOG_MIN)) * CHART_W));
}

export function BandChart({ rows, onRowClick, expandedDrug, ghostRows }: BandChartProps) {
  const h = rows.length * ROW_H + 30;

  const ticks = Array.from({ length: LOG_MAX - LOG_MIN + 1 }, (_, i) => LOG_MIN + i);

  return (
    <div>
      <svg
        width={W}
        height={h}
        viewBox={`0 0 ${W} ${h}`}
        className="w-full max-w-full"
        role="img"
        aria-label="Concentration band chart"
      >
        <title>Predicted concentration bands per drug</title>

        {/* x-axis ticks */}
        <g transform={`translate(${LABEL_W},${h - 20})`}>
          {ticks.map((t) => {
            const x = toX(Math.pow(10, t));
            return (
              <g key={t}>
                <line x1={x} y1={0} x2={x} y2={4} stroke="currentColor" strokeWidth={0.5} className="text-neutral-300 dark:text-neutral-600" />
                <text x={x} y={14} textAnchor="middle" fontSize={12} fill="currentColor" className="text-neutral-600 dark:text-neutral-400">
                  {t === 0 ? "1" : `10^${t}`}
                </text>
              </g>
            );
          })}
          <line x1={0} y1={0} x2={CHART_W} y2={0} stroke="currentColor" strokeWidth={0.5} className="text-neutral-200 dark:text-neutral-700" />
        </g>

        {/* rows */}
        {rows.map((row, i) => {
          const y = i * ROW_H + 6;
          const ghost = ghostRows?.find((g) => g.drug === row.drug);
          const selected = expandedDrug === row.drug;
          const fill = TIER_FILL[row.tier] ?? "#aaa";

          return (
            <g
              key={row.drug}
              transform={`translate(${LABEL_W},${y})`}
              onClick={() => onRowClick?.(row.drug)}
              className={onRowClick ? "cursor-pointer" : ""}
              tabIndex={onRowClick ? 0 : undefined}
              role={onRowClick ? "button" : undefined}
              aria-pressed={selected}
              onKeyDown={(e) => e.key === "Enter" && onRowClick?.(row.drug)}
            >
              {/* highlight selected */}
              {selected && (
                <rect x={-LABEL_W} y={-4} width={W} height={ROW_H} fill="currentColor" className="text-blue-50 dark:text-blue-950" rx={2} />
              )}
              {/* ghost band */}
              {ghost && (
                <rect
                  x={toX(ghost.p5)}
                  y={5}
                  width={Math.max(1, toX(ghost.p95) - toX(ghost.p5))}
                  height={10}
                  fill={fill}
                  opacity={0.2}
                  rx={2}
                />
              )}
              {/* p5-p95 band */}
              <rect
                x={toX(row.p5)}
                y={5}
                width={Math.max(1, toX(row.p95) - toX(row.p5))}
                height={10}
                fill={fill}
                opacity={0.6}
                rx={2}
              />
              {/* p50 tick */}
              <line x1={toX(row.p50)} y1={2} x2={toX(row.p50)} y2={18} stroke={fill} strokeWidth={2} />
              {/* PNEC line */}
              <line
                x1={toX(row.pnec)}
                y1={0}
                x2={toX(row.pnec)}
                y2={20}
                stroke="#6366f1"
                strokeWidth={1}
                strokeDasharray="3,2"
              />
              {/* LOD line */}
              {row.lod != null && (
                <line
                  x1={toX(row.lod)}
                  y1={0}
                  x2={toX(row.lod)}
                  y2={20}
                  stroke="var(--c-slate)"
                  strokeWidth={1}
                  strokeDasharray="2,2"
                />
              )}
              {/* drug label */}
              <text x={-8} y={13} textAnchor="end" fontSize={12} fill="currentColor" className="text-neutral-600 dark:text-neutral-400">
                {row.drug}
              </text>
            </g>
          );
        })}

        {/* legend */}
        <g transform={`translate(${LABEL_W},${h - 18})`}>
          <line x1={0} y1={-3} x2={12} y2={-3} stroke="var(--c-indigo-soft)" strokeWidth={1} strokeDasharray="3,2" />
          <text x={16} y={0} fontSize={12} fill="var(--c-indigo-soft)"><Term term="PNEC">PNEC</Term></text>
          <line x1={60} y1={-3} x2={72} y2={-3} stroke="var(--c-slate)" strokeWidth={1} strokeDasharray="2,2" />
          <text x={76} y={0} fontSize={12} fill="var(--c-slate)">LOD</text>
        </g>
      </svg>

      {/* PNEC/LOD info buttons outside SVG */}
      <div className="flex gap-4 mt-1 text-xs text-neutral-600 dark:text-neutral-400">
        {rows[0]?.pnecProvKey && (
          <span>
            <Term term="PNEC">PNEC</Term>
            <InfoButton provKey={rows[0].pnecProvKey} />
          </span>
        )}
        {rows[0]?.lodProvKey && (
          <span>
            LOD
            <InfoButton provKey={rows[0].lodProvKey} />
          </span>
        )}
      </div>

      <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
        Ranges under stated assumptions — see Methodology.
      </p>
    </div>
  );
}
