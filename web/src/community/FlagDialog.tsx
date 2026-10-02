/** Flag a public report: pick a reason; three different people holding it sends it back for review. */
import { useEffect, useState } from "react";
import { apiFetch } from "./api";
import { ErrorLine, Modal, outlineButton, primaryButton } from "./Modal";
import { useReports } from "./reportsStore";

export function FlagDialog() {
  const report = useReports((s) => s.flagging);
  const close = useReports((s) => s.closeFlag);
  const send = useReports((s) => s.sendFlag);
  const busy = useReports((s) => s.busy);
  const error = useReports((s) => s.error);
  const done = useReports((s) => s.flagDone);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (report && Object.keys(reasons).length === 0) {
      apiFetch<Record<string, string>>("/flag-reasons").then(setReasons).catch(() => undefined);
    }
  }, [report, reasons]);

  if (!report) return null;
  if (done) {
    return (
      <Modal title="Thank you" onClose={close}>
        <p className="mb-4" style={{ color: "var(--c-muted)" }}>Your flag was sent. A moderator will look at this report.</p>
        <button onClick={close} className="w-full px-4 py-2.5 rounded-lg font-semibold" style={primaryButton}>Close</button>
      </Modal>
    );
  }
  return (
    <Modal title="Flag this report" onClose={close}>
      <p className="text-sm mb-3" style={{ color: "var(--c-muted)" }}>What is wrong with it?</p>
      <div className="flex flex-col gap-2 mb-4" role="radiogroup" aria-label="Reason">
        {Object.entries(reasons).map(([id, label]) => (
          <label key={id} className="flex items-center gap-2">
            <input type="radio" name="flag-reason" checked={reason === id} onChange={() => setReason(id)} />
            {label}
          </label>
        ))}
      </div>
      <ErrorLine message={error} />
      <div className="flex gap-3">
        <button disabled={!reason || busy} onClick={() => void send(reason)} className="flex-1 px-4 py-2.5 rounded-lg font-semibold disabled:opacity-50" style={primaryButton}>
          {busy ? "Sending…" : "Send flag"}
        </button>
        <button onClick={close} className="px-4 py-2.5 rounded-lg font-medium" style={outlineButton}>Cancel</button>
      </div>
    </Modal>
  );
}
