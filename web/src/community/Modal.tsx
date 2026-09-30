/** A centred dialog with a dimmed backdrop. Escape and a click outside close it. */
import { useEffect, type ReactNode } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function Modal({ title, onClose, children }: ModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
      <div className="fixed inset-0" style={{ background: "rgba(0,0,0,0.5)" }} onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative w-full max-w-md rounded-xl p-6 max-h-[90vh] overflow-y-auto"
        style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)", color: "var(--c-text)" }}
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <h2 className="font-display text-2xl" style={{ fontWeight: 500 }}>{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-2xl leading-none"
            style={{ color: "var(--c-faint)" }}
          >
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

const fieldStyle = {
  background: "var(--c-canvas)",
  border: "1px solid var(--c-border)",
  color: "var(--c-text)",
} as const;

/** A labelled text input used by the community dialogs. */
export function Field(props: {
  label: string;
  hint?: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  autoComplete?: string;
  autoFocus?: boolean;
  maxLength?: number;
}) {
  return (
    <label className="block mb-4">
      <span className="block text-sm font-medium mb-1">{props.label}</span>
      <input
        type={props.type ?? "text"}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        autoComplete={props.autoComplete}
        autoFocus={props.autoFocus}
        maxLength={props.maxLength}
        className="w-full px-3 py-2 rounded-lg text-base focus:outline-none"
        style={fieldStyle}
      />
      {props.hint && <span className="block text-sm mt-1" style={{ color: "var(--c-muted2)" }}>{props.hint}</span>}
    </label>
  );
}

/** The error line shared by the dialogs (announced to screen readers). */
export function ErrorLine({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="text-sm rounded-lg px-3 py-2 mb-4"
      style={{ background: "var(--c-danger-bg)", color: "var(--c-danger-text)", border: "1px solid var(--c-danger-border)" }}
    >
      {message}
    </p>
  );
}

export const primaryButton = { background: "var(--c-accent)", color: "var(--c-on-accent)" } as const;
export const outlineButton = {
  border: "1px solid var(--c-border)",
  background: "var(--c-surface)",
  color: "var(--c-text)",
} as const;
