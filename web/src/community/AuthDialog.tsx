/** Sign in or create an account. Email and password, and Google when the Neon project has it enabled. */
import { useState, type FormEvent } from "react";
import { useCommunity } from "./store";
import { ErrorLine, Field, Modal, outlineButton, primaryButton } from "./Modal";

const GOOGLE_ENABLED = import.meta.env.VITE_NEON_AUTH_GOOGLE === "true";

export function AuthDialog() {
  const mode = useCommunity((s) => s.authDialog);
  const { busy, error } = useCommunity();
  const close = useCommunity((s) => s.closeAuthDialog);
  const open = useCommunity((s) => s.openAuthDialog);
  const signInEmail = useCommunity((s) => s.signInEmail);
  const signUpEmail = useCommunity((s) => s.signUpEmail);
  const signInGoogle = useCommunity((s) => s.signInGoogle);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (mode === "closed") return null;
  const signingUp = mode === "signup";

  function submit(e: FormEvent) {
    e.preventDefault();
    if (signingUp) void signUpEmail(name.trim() || email.split("@")[0], email.trim(), password);
    else void signInEmail(email.trim(), password);
  }

  return (
    <Modal title={signingUp ? "Create an account" : "Sign in"} onClose={close}>
      <form onSubmit={submit}>
        {signingUp && (
          <Field
            label="Your name"
            hint="Kept private. Other people only ever see the nickname you choose next."
            value={name}
            onChange={setName}
            autoComplete="name"
            autoFocus
          />
        )}
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" autoFocus={!signingUp} />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete={signingUp ? "new-password" : "current-password"}
          hint={signingUp ? "At least 8 characters." : undefined}
        />
        <ErrorLine message={error} />
        <button
          type="submit"
          disabled={busy || !email || password.length < (signingUp ? 8 : 1)}
          className="w-full px-4 py-2.5 rounded-lg font-semibold disabled:opacity-50"
          style={primaryButton}
        >
          {busy ? "One moment…" : signingUp ? "Create account" : "Sign in"}
        </button>
      </form>

      {GOOGLE_ENABLED && (
        <button
          onClick={() => void signInGoogle()}
          className="w-full mt-3 px-4 py-2.5 rounded-lg font-medium"
          style={outlineButton}
        >
          Continue with Google
        </button>
      )}

      <p className="text-sm mt-5" style={{ color: "var(--c-muted)" }}>
        {signingUp ? "Already have an account? " : "New here? "}
        <button
          onClick={() => open(signingUp ? "signin" : "signup")}
          className="underline font-medium"
          style={{ color: "var(--c-accent)" }}
        >
          {signingUp ? "Sign in" : "Create an account"}
        </button>
      </p>
      <p className="text-sm mt-3" style={{ color: "var(--c-muted2)" }}>
        Your email is used only to sign you in. Other people never see it, only your nickname.
      </p>
    </Modal>
  );
}
