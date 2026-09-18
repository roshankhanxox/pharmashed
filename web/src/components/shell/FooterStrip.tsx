import { useStore } from "../../data/store";

export function FooterStrip() {
  const results = useStore((s) => s.results);
  if (!results) return null;

  const { meta } = results;
  const frozen = meta.frozen_tag ?? "not frozen";
  const citedLabel = meta.all_params_cited
    ? "all cited"
    : `${meta.param_count} parameters (some uncited)`;

  return (
    <footer className="border-t border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-4 py-1.5 text-xs text-neutral-400 flex gap-4 flex-wrap">
      <span>N = {meta.n_draws.toLocaleString()} draws</span>
      <span>engine {meta.engine_version}</span>
      <span>predictions frozen: {frozen}</span>
      <span>{citedLabel}</span>
    </footer>
  );
}
