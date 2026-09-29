import { useStore, type Tab } from "../../data/store";
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
        {TABS.map((t) => {
          const active = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className="relative px-3 py-3.5 text-sm transition-colors shrink-0"
              style={{
                color: active ? "var(--c-text)" : "var(--c-muted2)",
                fontWeight: active ? 500 : 400,
                borderBottom: active ? "2px solid var(--c-indigo)" : "2px solid transparent",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </nav>

      <ThemeToggle />

      {/* Assistant CTA */}
      <button
        onClick={openAssistant}
        className="ml-3 shrink-0 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all"
        style={{
          background: "var(--c-indigo)",
          color: "#ffffff",
          letterSpacing: "0.04em",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "var(--c-indigo-deep)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "var(--c-indigo)"; }}
      >
        Assistant
      </button>
    </header>
  );
}
