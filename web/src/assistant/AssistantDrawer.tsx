import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStore } from "../data/store";
import { apiBase } from "../data/loaders";

const C = {
  canvas:  "#0c0a09",
  surface: "#1a1917",
  raised:  "#242220",
  border:  "#292524",
  text:    "#f5f4f2",
  muted:   "#a6a09b",
  faint:   "#6b6460",
  indigo:  "#7c75ff",
} as const;

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
  links?: Array<{ target_tab: string; site_id?: string; drug?: string; label: string }>;
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
    fetch(`${apiBase()}/assistant`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "ping" }),
    })
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
      <div className="fixed inset-0" style={{ background: "rgba(0,0,0,0.5)" }} onClick={close} />
      <aside
        className="relative z-10 w-[480px] max-w-full flex flex-col"
        style={{
          background: C.canvas,
          borderLeft: `1px solid ${C.border}`,
          boxShadow: "-8px 0 40px rgba(0,0,0,0.6)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-3 shrink-0"
          style={{ borderBottom: `1px solid ${C.border}` }}
        >
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full"
              style={{ background: apiAvailable === false ? C.faint : C.indigo }}
            />
            <h2 className="font-semibold text-sm" style={{ color: C.text }}>PharmaShed Assistant</h2>
            <span
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{ background: C.raised, color: C.faint, fontFamily: "ui-monospace, monospace", border: `1px solid ${C.border}` }}
            >
              Groq
            </span>
          </div>
          <button
            onClick={close}
            className="text-xl leading-none transition-colors"
            style={{ color: C.faint }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = C.text; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = C.faint; }}
          >
            ×
          </button>
        </div>

        {/* Unavailable banner */}
        {apiAvailable === false && (
          <div
            className="text-xs px-5 py-3 shrink-0"
            style={{ background: "#1c1400", borderBottom: `1px solid #78350f`, color: "#fbbf24" }}
          >
            Assistant unavailable — LLM API key not configured on the backend. Start the API server with <code style={{ fontFamily: "ui-monospace, monospace" }}>GROQ_API_KEY</code> set.
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4 scrollbar-none">
          {messages.length === 0 && (
            <div>
              <p className="text-xs mb-3" style={{ color: C.faint }}>Suggested questions:</p>
              <div className="flex flex-col gap-1.5">
                {SUGGESTED.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    disabled={apiAvailable === false}
                    className="text-left text-xs px-3 py-2 rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{ border: `1px solid ${C.border}`, color: C.muted, background: "transparent" }}
                    onMouseEnter={(e) => {
                      if (apiAvailable !== false) (e.currentTarget as HTMLButtonElement).style.borderColor = C.indigo;
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.borderColor = C.border;
                    }}
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
                    <span
                      key={j}
                      className="text-[10px] px-2 py-0.5 rounded-full"
                      style={{ background: C.raised, color: C.faint, fontFamily: "ui-monospace, monospace", border: `1px solid ${C.border}` }}
                    >
                      {tc.name}
                    </span>
                  ))}
                </div>
              )}

              <div
                className="max-w-[90%] rounded-xl px-4 py-3 text-sm"
                style={
                  m.role === "user"
                    ? { background: C.indigo, color: "#fff" }
                    : { background: C.surface, color: C.text, border: `1px solid ${C.border}` }
                }
              >
                <MarkdownText text={m.text} />
              </div>

              {/* Guard warning */}
              {m.guardWarn && (
                <div
                  className="text-[10px] rounded px-2 py-0.5"
                  style={{ background: "#1c1400", color: "#fbbf24", border: "1px solid #78350f" }}
                >
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
                        const tab = lnk.target_tab.toLowerCase() as Parameters<typeof setActiveTab>[0];
                        setActiveTab(tab);
                        if (lnk.site_id) setSelectedSiteId(lnk.site_id);
                        if (lnk.drug) setSelectedDrug(lnk.drug);
                        close();
                      }}
                      className="text-[10px] underline"
                      style={{ color: C.indigo }}
                    >
                      {lnk.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="text-sm animate-pulse" style={{ color: C.faint }}>Thinking…</div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Standing footer */}
        <div
          className="px-5 py-2 text-[10px] shrink-0"
          style={{ borderTop: `1px solid ${C.border}`, color: C.faint }}
        >
          Scores reflect assumed priors · assistant never computes values itself
        </div>

        {/* Input */}
        <div className="px-4 pb-4 shrink-0">
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
              className="flex-1 px-3 py-2 text-sm rounded-lg focus:outline-none disabled:opacity-40"
              style={{
                background: C.surface,
                border: `1px solid ${C.border}`,
                color: C.text,
              }}
              onFocus={(e) => { (e.currentTarget as HTMLInputElement).style.borderColor = C.indigo; }}
              onBlur={(e) => { (e.currentTarget as HTMLInputElement).style.borderColor = C.border; }}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading || apiAvailable === false}
              className="px-3 py-2 text-sm rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: C.indigo, color: "#fff" }}
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
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold" style={{ color: "#f5f4f2" }}>{children}</strong>,
        em: ({ children }) => <em className="italic">{children}</em>,
        code: ({ children, className }) => {
          const isBlock = !!className;
          return isBlock ? (
            <pre className="my-2 p-3 rounded-lg text-xs overflow-x-auto" style={{ background: "#0c0a09", color: "#a6a09b", fontFamily: "ui-monospace, monospace" }}>
              <code>{children}</code>
            </pre>
          ) : (
            <code className="px-1.5 py-0.5 rounded text-[11px]" style={{ background: "#0c0a09", color: "#a6a09b", fontFamily: "ui-monospace, monospace" }}>{children}</code>
          );
        },
        ul: ({ children }) => <ul className="list-disc list-outside ml-4 mb-2 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-outside ml-4 mb-2 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        table: ({ children }) => (
          <div className="my-2 overflow-x-auto">
            <table className="text-xs border-collapse w-full">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead>{children}</thead>,
        th: ({ children }) => (
          <th className="px-3 py-1.5 text-left font-semibold border-b" style={{ borderColor: "#292524", color: "#a6a09b" }}>{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-1.5 border-b" style={{ borderColor: "#1a1917", color: "#f5f4f2" }}>{children}</td>
        ),
        tr: ({ children }) => <tr className="hover:bg-white/5 transition-colors">{children}</tr>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 pl-3 my-2 italic" style={{ borderColor: "#7c75ff", color: "#a6a09b" }}>{children}</blockquote>
        ),
        h1: ({ children }) => <h1 className="text-base font-bold mb-2 mt-1">{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-semibold mb-1.5 mt-1">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-medium mb-1 mt-1">{children}</h3>,
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noreferrer" className="underline" style={{ color: "#7c75ff" }}>{children}</a>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
