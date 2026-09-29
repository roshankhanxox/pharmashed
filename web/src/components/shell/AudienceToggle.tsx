/**
 * Citizen / Expert view switch. Citizen view uses plain language and fewer tabs;
 * expert view is the full technical interface. The choice is stored by the store.
 */
import { useStore, type Audience } from "../../data/store";

const OPTIONS: { id: Audience; label: string }[] = [
  { id: "citizen", label: "Citizen" },
  { id: "expert", label: "Expert" },
];

export function AudienceToggle() {
  const audience = useStore((s) => s.audience);
  const setAudience = useStore((s) => s.setAudience);

  return (
    <div
      role="group"
      aria-label="Choose your view"
      className="shrink-0 flex items-center rounded-lg p-0.5"
      style={{ border: "1px solid var(--c-border)", background: "var(--c-raised)" }}
    >
      <span className="px-2 text-xs" style={{ color: "var(--c-faint)" }}>View</span>
      {OPTIONS.map((o) => {
        const active = audience === o.id;
        return (
          <button
            key={o.id}
            onClick={() => setAudience(o.id)}
            aria-pressed={active}
            className="px-3 py-1 text-sm rounded-md transition-colors"
            style={{
              background: active ? "var(--c-indigo)" : "transparent",
              color: active ? "#ffffff" : "var(--c-muted)",
              fontWeight: active ? 600 : 400,
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
