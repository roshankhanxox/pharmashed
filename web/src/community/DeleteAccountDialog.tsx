/** Confirm deleting the account. The person types their nickname so it cannot happen by accident. */
import { useState } from "react";
import { ErrorLine, Modal, outlineButton } from "./Modal";
import { useCommunity } from "./store";

export function DeleteAccountDialog() {
  const open = useCommunity((s) => s.deleteDialogOpen);
  const { busy, error, profile } = useCommunity();
  const close = useCommunity((s) => s.closeDeleteDialog);
  const remove = useCommunity((s) => s.deleteAccount);
  const [typed, setTyped] = useState("");
  if (!open) return null;
  const phrase = profile?.nickname ?? "delete";
  const ok = typed.trim().toLowerCase() === phrase.toLowerCase();

  return (
    <Modal title="Delete my account" onClose={close}>
      <p className="text-sm mb-3" style={{ color: "var(--c-muted)" }}>
        This permanently removes your profile, every report you filed, your photos, points and badges, and your sign-in.
        It cannot be undone. Other people's reports are not affected.
      </p>
      <label className="block mb-4">
        <span className="block text-sm font-medium mb-1">Type <strong>{phrase}</strong> to confirm</span>
        <input value={typed} onChange={(e) => setTyped(e.target.value)} autoFocus className="w-full px-3 py-2 rounded-lg text-base"
               style={{ background: "var(--c-canvas)", border: "1px solid var(--c-border)", color: "var(--c-text)" }} />
      </label>
      <ErrorLine message={error} />
      <div className="flex gap-3">
        <button disabled={!ok || busy} onClick={() => void remove().then((done) => done && setTyped(""))}
                className="flex-1 px-4 py-2.5 rounded-lg font-semibold disabled:opacity-50"
                style={{ background: "var(--c-danger-bg)", color: "var(--c-danger-text)", border: "1px solid var(--c-danger-border)" }}>
          {busy ? "Deleting…" : "Delete everything"}
        </button>
        <button onClick={close} className="px-4 py-2.5 rounded-lg font-medium" style={outlineButton}>Cancel</button>
      </div>
    </Modal>
  );
}
