/** Choose the public nickname (the only name anyone else sees), a home city, and leaderboard visibility. */
import { useState, type FormEvent } from "react";
import { useCommunity } from "./store";
import { ErrorLine, Field, Modal, outlineButton, primaryButton } from "./Modal";

export const CITIES = [
  { id: "TLS", name: "Toulouse" },
  { id: "GNT", name: "Ghent" },
  { id: "BNV", name: "Benevento" },
  { id: "CBR", name: "Coimbra" },
  { id: "OSL", name: "Oslo" },
];

/** Quick check for instant feedback; the server applies the full rules (reserved names, uniqueness). */
export function nicknameProblem(nickname: string): string | null {
  const n = nickname.trim();
  if (n.length < 3 || n.length > 20) return "Use 3 to 20 characters.";
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(n)) return "Use only letters, numbers, dashes and underscores.";
  if (!/[A-Za-z]/.test(n)) return "Include at least one letter.";
  return null;
}

export function NicknameDialog() {
  const open = useCommunity((s) => s.nicknameDialogOpen);
  const { busy, error, profile } = useCommunity();
  const close = useCommunity((s) => s.closeNicknameDialog);
  const save = useCommunity((s) => s.saveProfile);
  const [nickname, setNickname] = useState(profile?.nickname ?? "");
  const [city, setCity] = useState(profile?.home_city ?? "");
  const [visible, setVisible] = useState(profile?.show_on_leaderboard ?? true);

  if (!open) return null;
  const problem = nickname ? nicknameProblem(nickname) : null;

  function submit(e: FormEvent) {
    e.preventDefault();
    void save({ nickname: nickname.trim(), show_on_leaderboard: visible, home_city: city || null });
  }

  return (
    <Modal title={profile ? "Your profile" : "Choose a nickname"} onClose={close}>
      <p className="text-sm mb-4" style={{ color: "var(--c-muted)" }}>
        This is the only name other people will see. Pick anything you like, and avoid your real name if you prefer to stay private.
      </p>
      <form onSubmit={submit}>
        <Field
          label="Nickname"
          value={nickname}
          onChange={setNickname}
          autoFocus
          maxLength={20}
          hint={problem ?? "3 to 20 letters, numbers, dashes or underscores."}
        />
        <label className="block mb-4">
          <span className="block text-sm font-medium mb-1">Nearest city (optional)</span>
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full px-3 py-2 rounded-lg text-base"
            style={{ background: "var(--c-canvas)", border: "1px solid var(--c-border)", color: "var(--c-text)" }}
          >
            <option value="">Not in these cities</option>
            {CITIES.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 mb-5 text-sm" style={{ color: "var(--c-muted)" }}>
          <input type="checkbox" checked={visible} onChange={(e) => setVisible(e.target.checked)} />
          Show my nickname on the leaderboard
        </label>
        <ErrorLine message={error} />
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={busy || !nickname || problem !== null}
            className="flex-1 px-4 py-2.5 rounded-lg font-semibold disabled:opacity-50"
            style={primaryButton}
          >
            {busy ? "Saving…" : "Save"}
          </button>
          <button type="button" onClick={close} className="px-4 py-2.5 rounded-lg font-medium" style={outlineButton}>
            {profile ? "Cancel" : "Later"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
