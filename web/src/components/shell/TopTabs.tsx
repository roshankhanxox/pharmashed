import { useStore, type Tab } from "../../data/store";

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
      style={{ background: "#0c0a09", borderBottom: "1px solid #292524" }}
      className="flex items-center px-5 gap-1 shrink-0"
    >
      {/* Wordmark */}
      <button
        onClick={() => setActiveTab("home")}
        className="flex items-center mr-5 shrink-0 group"
      >
        <span
          className="text-sm font-semibold tracking-tight group-hover:opacity-60 transition-opacity"
          style={{ color: "#f5f4f2", fontFamily: "'Inter', sans-serif", letterSpacing: "-0.01em" }}
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
                color: active ? "#f5f4f2" : "#79716b",
                fontWeight: active ? 500 : 400,
                borderBottom: active ? "2px solid #7c75ff" : "2px solid transparent",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </nav>

      {/* Assistant CTA */}
      <button
        onClick={openAssistant}
        className="ml-auto shrink-0 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all"
        style={{
          background: "#7c75ff",
          color: "#ffffff",
          letterSpacing: "0.04em",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "#615fff"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "#7c75ff"; }}
      >
        Assistant
      </button>
    </header>
  );
}
