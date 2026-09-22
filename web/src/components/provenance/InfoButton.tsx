import { useStore } from "../../data/store";

export function InfoButton({ provKey }: { provKey: string }) {
  const openProvenance = useStore((s) => s.openProvenance);
  return (
    <button
      onClick={() => openProvenance(provKey)}
      className="inline-flex items-center justify-center w-4 h-4 rounded-full text-xs text-blue-500 border border-blue-300 hover:bg-blue-50 dark:hover:bg-blue-950 ml-1 align-middle"
      aria-label="Show provenance"
    >
      ⓘ
    </button>
  );
}
