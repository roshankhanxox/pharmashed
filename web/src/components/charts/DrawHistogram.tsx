/**
 * Histogram of log10 RQ draws with exceedance area and score label.
 */

export interface HistogramData {
  log10_edges: number[];
  counts: number[];
}

interface DrawHistogramProps {
  histogram: HistogramData;
  score: number;
}

const W = 400;
const H = 120;
const PAD = { top: 10, right: 20, bottom: 30, left: 40 };
const IW = W - PAD.left - PAD.right;
const IH = H - PAD.top - PAD.bottom;

export function DrawHistogram({ histogram, score }: DrawHistogramProps) {
  const { log10_edges, counts } = histogram;
  const maxCount = Math.max(...counts, 1);
  const n = counts.length;
  const binW = IW / n;
  const rq1X = ((0 - log10_edges[0]) / (log10_edges[log10_edges.length - 1] - log10_edges[0])) * IW;

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-full max-w-full" role="img">
      <title>Distribution of RQ draws</title>
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {/* bars */}
        {counts.map((c, i) => {
          const barH = (c / maxCount) * IH;
          const x = i * binW;
          const isExceedance = log10_edges[i] >= 0;
          return (
            <rect
              key={i}
              x={x + 1}
              y={IH - barH}
              width={binW - 2}
              height={barH}
              fill={isExceedance ? "#ef4444" : "#60a5fa"}
              opacity={0.7}
            />
          );
        })}

        {/* RQ=1 vertical line */}
        {rq1X >= 0 && rq1X <= IW && (
          <>
            <line x1={rq1X} y1={0} x2={rq1X} y2={IH} stroke="#111" strokeWidth={1.5} />
            <text x={rq1X + 3} y={10} fontSize={9} fill="#111">RQ = 1</text>
          </>
        )}

        {/* score label */}
        <text x={IW} y={10} textAnchor="end" fontSize={10} fill="#ef4444">
          score = {score.toFixed(3)} (share with RQ &gt; 1)
        </text>

        {/* axes */}
        <line x1={0} y1={IH} x2={IW} y2={IH} stroke="#ccc" />
        <line x1={0} y1={0} x2={0} y2={IH} stroke="#ccc" />

        {/* x labels */}
        {log10_edges.map((e, i) => (
          <text key={i} x={i * binW} y={IH + 12} fontSize={8} fill="#888" textAnchor="middle">
            {e === 0 ? "1" : `10^${e}`}
          </text>
        ))}

        <text x={IW / 2} y={IH + 25} fontSize={9} fill="#888" textAnchor="middle">
          log₁₀ RQ
        </text>
      </g>
    </svg>
  );
}
