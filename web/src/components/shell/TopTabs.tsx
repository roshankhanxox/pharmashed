import { useStore, type Tab } from "../../data/store";

const TABS: { id: Tab; label: string }[] = [
  { id: "explore", label: "Explore" },
  { id: "scenarios", label: "Scenarios" },
  { id: "consistency", label: "Consistency" },
  { id: "methodology", label: "Methodology" },
  { id: "fhir", label: "FHIR" },
];

export function TopTabs() {
  const activeTab = useStore((s) => s.activeTab);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const openAssistant = useStore((s) => s.openAssistant);

  return (
    <header className="border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 flex items-center px-4 gap-1">
      <span className="font-semibold text-sm text-neutral-800 dark:text-neutral-100 mr-4 shrink-0">
        PharmaShed
      </span>
      <nav className="flex gap-0.5 flex-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-3 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === t.id
                ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                : "border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <button
        onClick={openAssistant}
        className="ml-auto shrink-0 px-3 py-1.5 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors"
      >
        Assistant
      </button>
    </header>
  );
}
