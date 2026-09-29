import { useStore } from "../../data/store";
import { DEMO_NOTICE } from "../../data/copy";

export function FooterStrip() {
  const results = useStore((s) => s.results);
  const audience = useStore((s) => s.audience);
  if (!results) return null;

  const { meta } = results;
  const frozen = meta.frozen_tag ?? "not frozen";
  const citedLabel = meta.all_params_cited
    ? "all cited"
    : `${meta.param_count} parameters (some uncited)`;

  return (
    <footer
      className="px-4 py-1.5 text-xs flex gap-4 flex-wrap shrink-0"
      style={{
        borderTop: "1px solid var(--c-border)",
        background: "var(--c-canvas)",
        color: "var(--c-faint)",
        letterSpacing: "0.02em",
      }}
    >
      {audience === "citizen" ? (
        <span>{DEMO_NOTICE}</span>
      ) : (
        <>
          <span>N = {meta.n_draws.toLocaleString()} draws</span>
          <span>engine {meta.engine_version}</span>
          <span>predictions frozen: {frozen}</span>
          <span>{citedLabel}</span>
        </>
      )}
    </footer>
  );
}
