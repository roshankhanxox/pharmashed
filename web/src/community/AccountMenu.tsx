/** Top-bar account control: "Sign in" when signed out, the nickname with a small menu when signed in. */
import { useState } from "react";
import { useCommunity } from "./store";
import { outlineButton } from "./Modal";

export function AccountMenu() {
  const { availability, signedIn, profile, userName } = useCommunity();
  const openAuthDialog = useCommunity((s) => s.openAuthDialog);
  const openNicknameDialog = useCommunity((s) => s.openNicknameDialog);
  const signOut = useCommunity((s) => s.signOut);
  const openPrivacy = useCommunity((s) => s.openPrivacy);
  const openDeleteDialog = useCommunity((s) => s.openDeleteDialog);
  const [open, setOpen] = useState(false);

  if (availability !== "ready") return null;

  if (!signedIn) {
    return (
      <button onClick={() => openAuthDialog("signin")} className="shrink-0 px-3 py-1.5 text-sm rounded-lg font-medium" style={outlineButton}>
        Sign in
      </button>
    );
  }

  const label = profile?.nickname ?? "Choose a nickname";
  return (
    <div className="relative shrink-0">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="px-3 py-1.5 text-sm rounded-lg font-medium"
        style={outlineButton}
      >
        {label} ▾
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            role="menu"
            className="absolute right-0 mt-1 z-50 w-52 rounded-lg py-1 text-sm"
            style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)", boxShadow: "0 8px 24px rgba(0,0,0,0.15)" }}
          >
            {userName && <div className="px-3 py-1.5" style={{ color: "var(--c-muted2)" }}>Signed in as {userName}</div>}
            <button
              role="menuitem"
              className="block w-full text-left px-3 py-2"
              onClick={() => { setOpen(false); openNicknameDialog(); }}
            >
              {profile ? "Edit profile" : "Choose a nickname"}
            </button>
            <button
              role="menuitem"
              className="block w-full text-left px-3 py-2"
              onClick={() => { setOpen(false); void signOut(); }}
            >
              Sign out
            </button>
            <button role="menuitem" className="block w-full text-left px-3 py-2" onClick={() => { setOpen(false); openPrivacy(); }}>
              Privacy
            </button>
            <button role="menuitem" className="block w-full text-left px-3 py-2" style={{ color: "var(--c-danger-text)" }}
                    onClick={() => { setOpen(false); openDeleteDialog(); }}>
              Delete my account
            </button>
          </div>
        </>
      )}
    </div>
  );
}
