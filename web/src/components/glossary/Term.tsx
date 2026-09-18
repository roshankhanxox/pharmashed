import { useState } from "react";

const DEFINITIONS: Record<string, string> = {
  PEC: "Predicted Environmental Concentration — the modelled drug concentration in the stream, in ng/L.",
  PNEC: "Predicted No-Effect Concentration — the threshold below which ecological harm is considered unlikely, in ng/L.",
  RQ: "Risk Quotient (PEC/PNEC) — values above 1 indicate exceedance of the no-effect threshold under stated priors.",
  "λ": "Leakage fraction — the share of wastewater that bypasses treatment and enters the stream directly.",
  Q: "Stream flow (dilution) — higher flow means more dilution of the drug.",
  score:
    'Sampling priority score — share of Monte Carlo draws with RQ > 1, under stated priors. This is NOT a probability; do not interpret it as one.',
};

export function Term({ term, children }: { term: string; children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const def = DEFINITIONS[term];

  return (
    <span className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="underline decoration-dotted cursor-help text-inherit"
        aria-label={`Definition of ${term}`}
      >
        {children ?? term}
      </button>
      {open && def && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute z-50 bottom-full left-0 mb-1 w-64 rounded-md bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 shadow-lg p-3 text-xs text-neutral-700 dark:text-neutral-300">
            <strong className="block mb-1">{term}</strong>
            {def}
          </div>
        </>
      )}
    </span>
  );
}
