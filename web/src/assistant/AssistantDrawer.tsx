import { useState, useRef, useEffect } from "react";
import { useStore } from "../data/store";
import { apiBase } from "../data/loaders";

const SUGGESTED: string[] = [
  "Which Toulouse sites should I sample first for irbesartan?",
  "What drives the score at the top-ranked Oslo site?",
  "Where does the PNEC for irbesartan come from?",
  "What would happen if leakage were halved at TLS-001?",
];

interface ToolCall {
  name: string;
}

interface Message {
  role: "user" | "assistant";
  text: string;
  toolCalls?: ToolCall[];
  guardWarn?: boolean;
  links?: Array<{ tab: string; site_id?: string; drug?: string; label: string }>;
}

export function AssistantDrawer() {
  const open = useStore((s) => s.assistantOpen);
  const close = useStore((s) => s.closeAssistant);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const setSelectedSiteId = useStore((s) => s.setSelectedSiteId);
  const setSelectedDrug = useStore((s) => s.setSelectedDrug);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiAvailable, setApiAvailable] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Check API availability on first open
  useEffect(() => {
    if (!open || apiAvailable !== null) return;
    fetch(`${apiBase()}/assistant`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: "ping" }) })
      .then((r) => setApiAvailable(r.status !== 503))
      .catch(() => setApiAvailable(false));
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(`${apiBase()}/assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json() as {
        answer_markdown?: string;
        tool_calls?: ToolCall[];
        links?: Message["links"];
        guard?: { status: string };
        detail?: string;
      };
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: data.answer_markdown ?? data.detail ?? "No answer received.",
          toolCalls: data.tool_calls,
          guardWarn: data.guard?.status === "warn",
          links: data.links,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Error: ${(e as Error).message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="fixed inset-0 bg-black/20" onClick={close} />
      <aside className="relative z-10 w-[480px] max-w-full bg-white dark:bg-neutral-950 border-l border-neutral-200 dark:border-neutral-800 flex flex-col shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-neutral-200 dark:border-neutral-800">
          <h2 className="font-semibold text-sm">PharmaShed Assistant</h2>
          <button onClick={close} className="text-neutral-400 hover:text-neutral-700 text-xl leading-none">×</button>
        </div>

        {/* Unavailable banner */}
        {apiAvailable === false && (
          <div className="bg-amber-50 text-amber-800 text-xs px-5 py-3 border-b border-amber-200">
            Assistant unavailable in static demo mode — ANTHROPIC_API_KEY not configured.
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
          {messages.length === 0 && (
            <div>
              <p className="text-xs text-neutral-400 mb-3">Suggested questions:</p>
              <div className="flex flex-col gap-1.5">
                {SUGGESTED.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    disabled={apiAvailable === false}
                    className="text-left text-xs px-3 py-2 rounded-lg border border-neutral-200 hover:border-blue-400 hover:bg-blue-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col gap-1 ${m.role === "user" ? "items-end" : "items-start"}`}>
              {/* Tool chips */}
              {m.toolCalls && m.toolCalls.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {m.toolCalls.map((tc, j) => (
                    <span key={j} className="text-[10px] px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 font-mono">
                      {tc.name}
                    </span>
                  ))}
                </div>
              )}

              <div className={`max-w-[90%] rounded-xl px-4 py-3 text-sm ${
                m.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-neutral-100 dark:bg-neutral-900 text-neutral-800 dark:text-neutral-200"
              }`}>
                <MarkdownText text={m.text} />
              </div>

              {/* Guard warning */}
              {m.guardWarn && (
                <div className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-0.5">
                  ⚠ Some numbers could not be verified against tool results
                </div>
              )}

              {/* Links */}
              {m.links && m.links.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {m.links.map((lnk, j) => (
                    <button
                      key={j}
                      onClick={() => {
                        setActiveTab(lnk.tab as Parameters<typeof setActiveTab>[0]);
                        if (lnk.site_id) setSelectedSiteId(lnk.site_id);
                        if (lnk.drug) setSelectedDrug(lnk.drug);
                        close();
                      }}
                      className="text-[10px] text-blue-600 underline"
                    >
                      {lnk.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="text-sm text-neutral-400 animate-pulse">Thinking…</div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Standing footer */}
        <div className="px-5 py-2 border-t border-neutral-100 dark:border-neutral-800 text-[10px] text-neutral-400">
          Scores reflect assumed priors; this assistant never computes values itself.
        </div>

        {/* Input */}
        <div className="px-4 pb-4">
          <form
            onSubmit={(e) => { e.preventDefault(); send(input); }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={apiAvailable === false || loading}
              placeholder="Ask about sites, scores, drivers…"
              className="flex-1 px-3 py-2 text-sm border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-900 focus:outline-none focus:border-blue-400 disabled:opacity-40"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading || apiAvailable === false}
              className="px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </form>
        </div>
      </aside>
    </div>
  );
}

function MarkdownText({ text }: { text: string }) {
  // Minimal: bold **x**, code `x`, line breaks
  const lines = text.split("\n");
  return (
    <>
      {lines.map((line, i) => (
        <span key={i}>
          {line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, j) => {
            if (part.startsWith("**") && part.endsWith("**")) {
              return <strong key={j}>{part.slice(2, -2)}</strong>;
            }
            if (part.startsWith("`") && part.endsWith("`")) {
              return <code key={j} className="bg-neutral-200 dark:bg-neutral-800 px-1 rounded text-xs font-mono">{part.slice(1, -1)}</code>;
            }
            return part;
          })}
          {i < lines.length - 1 && <br />}
        </span>
      ))}
    </>
  );
}
