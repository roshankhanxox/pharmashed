/**
 * Light/dark theme switch. Toggles the `dark` class on <html> (which drives the
 * --c-* tokens and Tailwind's dark: variant) and remembers the choice in localStorage.
 */
import { useState } from "react";

const STORAGE_KEY = "ps-theme";

/** Reads the current theme from the <html> class. */
function currentIsDark(): boolean {
  return document.documentElement.classList.contains("dark");
}

export function ThemeToggle() {
  const [dark, setDark] = useState<boolean>(currentIsDark);

  function toggle() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem(STORAGE_KEY, next ? "dark" : "light");
    } catch {
      /* storage unavailable (private window) — the theme still applies for this visit */
    }
    setDark(next);
  }

  return (
    <button
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Switch to light theme" : "Switch to dark theme"}
      className="shrink-0 px-3 py-1.5 text-sm rounded-lg transition-colors"
      style={{ color: "var(--c-muted)", border: "1px solid var(--c-border)", background: "transparent" }}
    >
      {dark ? "☀ Light" : "☾ Dark"}
    </button>
  );
}
