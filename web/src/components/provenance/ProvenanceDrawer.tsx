import { useStore } from "../../data/store";

export function ProvenanceDrawer() {
  const key = useStore((s) => s.provenanceKey);
  const provenance = useStore((s) => s.provenance);
  const close = useStore((s) => s.closeProvenance);

  if (!key) return null;

  const entry = provenance ? (provenance as Record<string, unknown>)[key] : null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="fixed inset-0 bg-black/30" onClick={close} />
      <aside className="relative z-10 w-80 bg-white dark:bg-neutral-900 border-l border-neutral-200 dark:border-neutral-700 p-5 overflow-y-auto flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-sm">Provenance</h2>
          <button onClick={close} className="text-neutral-600 dark:text-neutral-400 hover:text-neutral-700 text-lg leading-none">×</button>
        </div>
        <p className="text-xs text-neutral-600 dark:text-neutral-400 font-mono break-all">{key}</p>
        {!entry ? (
          <p className="text-sm text-neutral-500">No provenance entry found for this key.</p>
        ) : (
          <ProvEntry entry={entry as ProvEntryData} />
        )}
      </aside>
    </div>
  );
}

interface ProvEntryData {
  label?: string;
  value?: number;
  unit?: string;
  distribution?: string;
  source_title?: string;
  source_url?: string;
  source_note?: string;
  status?: string;
}

function ProvEntry({ entry }: { entry: ProvEntryData }) {
  return (
    <dl className="text-sm space-y-3">
      {entry.value != null && (
        <Row label="Value">
          {entry.value} {entry.unit && <span className="text-neutral-600 dark:text-neutral-400">{entry.unit}</span>}
        </Row>
      )}
      {entry.distribution && <Row label="Distribution">{entry.distribution}</Row>}
      {entry.status && (
        <Row label="Status">
          <span className={`px-1.5 py-0.5 rounded text-xs ${
            entry.status === "sourced"
              ? "bg-green-100 text-green-800"
              : entry.status === "todo"
              ? "bg-yellow-100 text-yellow-800"
              : "bg-neutral-100 text-neutral-600"
          }`}>
            {entry.status}
          </span>
        </Row>
      )}
      {entry.source_title && (
        <Row label="Source">
          {entry.source_url ? (
            <a href={entry.source_url} target="_blank" rel="noreferrer" className="text-blue-600 underline">
              {entry.source_title}
            </a>
          ) : (
            entry.source_title
          )}
        </Row>
      )}
      {entry.source_note && (
        <Row label="Note">
          <span className="text-neutral-500">{entry.source_note}</span>
        </Row>
      )}
    </dl>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-neutral-600 dark:text-neutral-400 uppercase tracking-wide mb-0.5">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}
