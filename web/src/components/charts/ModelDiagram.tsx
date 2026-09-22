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
    <div className="overflow-x-auto">
      <div className="flex items-stretch gap-0 min-w-max">
        {stages.map((stage, i) => (
          <div key={stage.id} className="flex items-center">
            <div className="flex flex-col items-center justify-center border border-neutral-200 dark:border-neutral-700 rounded-lg p-3 w-36 bg-white dark:bg-neutral-900 shadow-sm">
              <span className="text-2xl font-serif text-blue-600 dark:text-blue-400 mb-1">
                {stage.symbol}
              </span>
              <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300 text-center">
                {stage.name}
              </span>
              <span className="text-xs text-neutral-400 text-center mt-1 leading-tight">
                {stage.prior_summary}
              </span>
              {stage.provenance_key && (
                <InfoButton provKey={stage.provenance_key} />
              )}
            </div>
            {i < stages.length - 1 && (
              <div className="text-neutral-300 dark:text-neutral-600 text-lg mx-1">→</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
