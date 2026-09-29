/**
 * Ask bar with starter questions. Typing a question (or clicking a starter) opens the
 * assistant drawer and sends it. Used on the Home pages so the assistant is the first thing
 * a visitor can act on, not just a button in the corner.
 */
import { useState } from "react";
import { useStore } from "../../data/store";

const STARTERS_CITIZEN = [
  "Which streams in Toulouse should be tested first?",
  "What does testing priority mean?",
  "Why do medicines in streams matter?",
];
const STARTERS_EXPERT = [
  "Which Toulouse sites should I sample first for irbesartan?",
  "What drives the score at the top-ranked Oslo site?",
  "Where does the PNEC for irbesartan come from?",
];

export function AskBar() {
  const citizen = useStore((s) => s.audience) === "citizen";
  const openAssistantWith = useStore((s) => s.openAssistantWith);
  const [text, setText] = useState("");
  const starters = citizen ? STARTERS_CITIZEN : STARTERS_EXPERT;

  function submit(question: string) {
    const q = question.trim();
    if (!q) return;
    setText("");
    openAssistantWith(q);
  }

  return (
    <div className="w-full max-w-2xl">
      <form
        onSubmit={(e) => { e.preventDefault(); submit(text); }}
        className="flex gap-2 rounded-xl p-2"
        style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)", boxShadow: "0 1px 2px rgba(0,0,0,0.06)" }}
      >
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={citizen ? "Ask anything about a stream or a medicine…" : "Ask about sites, scores, drivers…"}
          aria-label="Ask the PharmaShed assistant"
          className="flex-1 min-w-0 px-3 py-2 text-base bg-transparent focus:outline-none"
          style={{ color: "var(--c-text)" }}
        />
        <button
          type="submit"
          disabled={!text.trim()}
          className="px-5 py-2 rounded-lg font-semibold disabled:opacity-40"
          style={{ background: "var(--c-accent)", color: "#fff" }}
        >
          Ask
        </button>
      </form>
      <div className="flex gap-2 flex-wrap mt-3">
        {starters.map((q) => (
          <button
            key={q}
            onClick={() => submit(q)}
            className="text-sm px-3 py-1.5 rounded-full text-left"
            style={{ border: "1px solid var(--c-border)", color: "var(--c-muted)", background: "transparent" }}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
