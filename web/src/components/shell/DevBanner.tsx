/**
 * Status banners for data that is not sourced (D16, D34).
 * Red: dev-mode placeholders filled in for missing parameters. Amber: every parameter is present
 * but some are declared illustrative.
 */

export function DevBanner() {
  return (
    <div className="bg-red-600 text-white text-xs font-mono text-center py-1 px-4">
      DEV — placeholder data, not sourced values. Do not cite.
    </div>
  );
}

export function PrototypeBanner() {
  return (
    <div
      className="text-sm text-center py-1.5 px-4"
      style={{
        background: "var(--c-warn-bg)",
        color: "var(--c-warn-text)",
        borderBottom: "1px solid var(--c-warn-border)",
      }}
    >
      Prototype: the drug parameters behind these numbers are illustrative placeholders, not sourced values.
    </div>
  );
}
