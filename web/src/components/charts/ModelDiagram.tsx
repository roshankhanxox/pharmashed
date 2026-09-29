/**
 * Horizontal pipeline diagram: Consumption → Excretion → Pathways → Dilution → In-stream → RQ
 */

import { InfoButton } from "../provenance/InfoButton";

export interface DiagramStage {
  id: string;
  name: string;
  symbol: string;
  prior_summary: string;
  provenance_key?: string;
}

export function ModelDiagram({ stages }: { stages: DiagramStage[] }) {
  return (
    <div>
      <div className="flex flex-wrap items-stretch gap-y-3">
        {stages.map((stage, i) => (
          <div key={stage.id} className="flex items-stretch">
            <div className="flex flex-col items-center justify-center border border-neutral-200 dark:border-neutral-700 rounded-lg p-3 w-40 bg-white dark:bg-neutral-900 shadow-sm">
              <span className="text-2xl font-serif text-blue-600 dark:text-blue-400 mb-1">
                {stage.symbol}
              </span>
              <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300 text-center">
                {stage.name}
              </span>
              <span className="text-xs text-neutral-600 dark:text-neutral-400 text-center mt-1 leading-tight">
                {stage.prior_summary}
              </span>
              {stage.provenance_key && (
                <InfoButton provKey={stage.provenance_key} />
              )}
            </div>
            {i < stages.length - 1 && (
              <div className="self-center text-neutral-500 dark:text-neutral-500 text-lg mx-1.5">→</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
