import { useStore, type Tab } from "../../data/store";
import { CITIZEN_TAB_LABEL } from "../../data/copy";
import { AudienceToggle } from "./AudienceToggle";
import { ThemeToggle } from "./ThemeToggle";

const TABS: { id: Tab; label: string }[] = [
  { id: "home",        label: "Home" },
  { id: "explore",     label: "Explore" },
  { id: "scenarios",   label: "Scenarios" },
  { id: "consistency", label: "Consistency" },
  { id: "methodology", label: "Methodology" },
  { id: "fhir",        label: "FHIR" },
];

export function TopTabs() {
  const activeTab    = useStore((s) => s.activeTab);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const openAssistant = useStore((s) => s.openAssistant);
  const audience     = useStore((s) => s.audience);

  // Citizen view shows only the tabs that have a citizen version.
  const tabs = audience === "citizen"
    ? TABS.filter((t) => t.id in CITIZEN_TAB_LABEL).map((t) => ({ ...t, label: CITIZEN_TAB_LABEL[t.id] ?? t.label }))
    : TABS;

  return (
    <header
      style={{ background: "var(--c-surface)", borderBottom: "1px solid var(--c-border)" }}
      className="flex items-center px-5 gap-1 shrink-0"
    >
      {/* Wordmark */}
      <button
        onClick={() => setActiveTab("home")}
        className="flex items-center mr-5 shrink-0 group"
      >
        <span
          className="text-sm font-semibold tracking-tight group-hover:opacity-60 transition-opacity"
          style={{ color: "var(--c-text)", fontFamily: "'Inter', sans-serif", letterSpacing: "-0.01em" }}
        >
          PharmaShed
        </span>
      </button>

      {/* Nav tabs */}
      <nav className="flex gap-0 flex-1 overflow-x-auto scrollbar-none">
        {tabs.map((t) => {
          const active = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className="relative px-3 py-3.5 text-sm transition-colors shrink-0"
              style={{
                color: active ? "var(--c-text)" : "var(--c-muted2)",
                fontWeight: active ? 500 : 400,
                borderBottom: active ? "2px solid var(--c-accent)" : "2px solid transparent",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <AudienceToggle />
        <ThemeToggle />
      </div>

      {/* Assistant CTA */}
      <button
        onClick={openAssistant}
        className="ml-3 shrink-0 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all"
        style={{
          background: "var(--c-accent)",
          color: "#ffffff",
          letterSpacing: "0.04em",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "var(--c-accent-deep)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "var(--c-accent)"; }}
      >
        Assistant
      </button>
    </header>
  );
}
