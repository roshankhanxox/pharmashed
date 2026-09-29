/**
 * Floating "Ask" button, bottom-right on every tab, so the assistant is one click away
 * wherever the visitor is. Hidden while the drawer is open.
 */
import { useStore } from "../../data/store";

export function FloatingAsk() {
  const open = useStore((s) => s.assistantOpen);
  const openAssistant = useStore((s) => s.openAssistant);
  const citizen = useStore((s) => s.audience) === "citizen";
  if (open) return null;

  return (
    <button
      onClick={openAssistant}
      aria-label="Open the PharmaShed assistant"
      className="fixed z-40 right-5 bottom-14 flex items-center gap-2 px-5 py-3 rounded-full font-semibold"
      style={{
        background: "var(--c-accent)",
        color: "var(--c-on-accent)",
        boxShadow: "0 6px 20px color-mix(in srgb, var(--c-accent) 35%, transparent)",
      }}
    >
      <span aria-hidden="true">✦</span>
      {citizen ? "Ask a question" : "Ask PharmaShed"}
    </button>
  );
}
