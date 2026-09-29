import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStore } from "../data/store";
import { apiBase } from "../data/loaders";

const C = {
  canvas:  "var(--c-canvas)",
  surface: "var(--c-surface)",
  raised:  "var(--c-raised)",
  border:  "var(--c-border)",
  text:    "var(--c-text)",
  muted:   "var(--c-muted)",
  faint:   "var(--c-faint)",
  indigo:  "var(--c-indigo)",
} as const;

const SUGGESTED: string[] = [
  "Which Toulouse sites should I sample first for irbesartan?",
  "What drives the score at the top-ranked Oslo site?",
  "Where does the PNEC for irbesartan come from?",
  "What would happen if leakage were halved at TLS-001?",
];

/** Starter questions for citizen view: plain wording, no model terms. */
const SUGGESTED_CITIZEN: string[] = [
  "Which streams in Toulouse should be tested first?",
  "What does testing priority mean?",
  "Why do medicines in streams matter?",
  "What would repairing sewers change at the top site?",
];

/** Starter questions about one site, worded for the current audience. */
function siteSuggestions(siteId: string, drug: string | null, citizen: boolean): string[] {
  if (citizen) {
    return [
      `Why does ${siteId} have this testing priority?`,
      `Which medicine matters most at ${siteId}?`,
      `What would repairing the sewers change at ${siteId}?`,
      "What does this ranking mean, and what doesn't it mean?",
    ];
  }
  return [
    `What drives the sampling priority score at ${siteId}?`,
    `What would flip ${siteId} to a different tier?`,
    drug ? `Where does the PNEC for ${drug} come from?` : `Where do the PNEC values used at ${siteId} come from?`,
    `What happens at ${siteId} if leakage is halved?`,
  ];
}

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
  const citizen = useStore((s) => s.audience) === "citizen";
  const close = useStore((s) => s.closeAssistant);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const setSelectedSiteId = useStore((s) => s.setSelectedSiteId);
  const setSelectedDrug = useStore((s) => s.setSelectedDrug);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiAvailable, setApiAvailable] = useState<boolean | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const context = useStore((s) => s.assistantContext);
  const clearContext = useStore((s) => s.clearAssistantContext);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Check on first open whether the backend has an API key. This is a plain GET, so it
  // does not spend a model call (the old check sent a real "ping" question).
  useEffect(() => {
    if (!open || apiAvailable !== null) return;
    fetch(`${apiBase()}/assistant/status`)
      .then((r) => r.json() as Promise<{ available: boolean; provider: string | null }>)
      .then((s) => {
        setApiAvailable(s.available);
        setProvider(s.provider);
      })
      .catch(() => setApiAvailable(false));
  }, [open, apiAvailable]);

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
        body: JSON.stringify({
          question,
          context: context ? { site_id: context.siteId, drug: context.drug } : undefined,
        }),
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
              className="text-xs px-1.5 py-0.5 rounded"
              style={{ background: C.raised, color: C.faint, border: `1px solid ${C.border}` }}
            >
              {provider === "openai" ? "OpenAI" : provider === "groq" ? "Groq" : "LLM"}
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
            style={{ background: "var(--c-warn-bg)", borderBottom: `1px solid var(--c-warn-border)`, color: "var(--c-warn-text)" }}
          >
            Assistant unavailable — LLM API key not configured on the backend. Start the API server with <code>OPENAI_API_KEY</code> (or <code>GROQ_API_KEY</code>) set.
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4 scrollbar-none">
          {messages.length === 0 && (
            <div>
              <p className="text-xs mb-3" style={{ color: C.faint }}>Suggested questions:</p>
              <div className="flex flex-col gap-1.5">
                {(context
                  ? siteSuggestions(context.siteId, context.drug, citizen)
                  : citizen ? SUGGESTED_CITIZEN : SUGGESTED
                ).map((q) => (
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
                      className="text-xs px-2 py-0.5 rounded-full"
                      style={{ background: C.raised, color: C.faint, border: `1px solid ${C.border}` }}
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
                  className="text-xs rounded px-2 py-0.5"
                  style={{ background: "var(--c-warn-bg)", color: "var(--c-warn-text)", border: "1px solid var(--c-warn-border)" }}
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
                      className="text-xs underline"
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
          className="px-5 py-2 text-xs shrink-0"
          style={{ borderTop: `1px solid ${C.border}`, color: C.faint }}
        >
          Scores reflect assumed priors · assistant never computes values itself
        </div>

        {/* Input */}
        <div className="px-4 pb-4 shrink-0">
          {context && (
            <div
              className="flex items-center gap-2 mb-2 text-xs rounded-lg px-3 py-1.5 w-fit max-w-full"
              style={{ background: C.raised, color: C.muted, border: `1px solid ${C.border}` }}
            >
              <span className="truncate">
                Asking about <strong style={{ color: C.text }}>{context.siteId}{context.drug ? ` · ${context.drug}` : ""}</strong>
              </span>
              <button
                onClick={clearContext}
                aria-label="Stop asking about this site"
                title="Ask about anything instead"
                className="leading-none"
                style={{ color: C.faint }}
              >
                ×
              </button>
            </div>
          )}
          <form
            onSubmit={(e) => { e.preventDefault(); send(input); }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={apiAvailable === false || loading}
              placeholder={context ? `Ask about ${context.siteId}…` : "Ask about sites, scores, drivers…"}
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
        strong: ({ children }) => <strong className="font-semibold" style={{ color: "var(--c-text)" }}>{children}</strong>,
        em: ({ children }) => <em className="italic">{children}</em>,
        code: ({ children, className }) => {
          const isBlock = !!className;
          return isBlock ? (
            <pre className="my-2 p-3 rounded-lg text-xs overflow-x-auto" style={{ background: "var(--c-canvas)", color: "var(--c-muted)" }}>
              <code>{children}</code>
            </pre>
          ) : (
            <code className="px-1.5 py-0.5 rounded text-[11px]" style={{ background: "var(--c-canvas)", color: "var(--c-muted)" }}>{children}</code>
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
          <th className="px-3 py-1.5 text-left font-semibold border-b" style={{ borderColor: "var(--c-border)", color: "var(--c-muted)" }}>{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-1.5 border-b" style={{ borderColor: "var(--c-surface)", color: "var(--c-text)" }}>{children}</td>
        ),
        tr: ({ children }) => <tr className="hover:bg-white/5 transition-colors">{children}</tr>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 pl-3 my-2 italic" style={{ borderColor: "var(--c-indigo)", color: "var(--c-muted)" }}>{children}</blockquote>
        ),
        h1: ({ children }) => <h1 className="text-base font-bold mb-2 mt-1">{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-semibold mb-1.5 mt-1">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-medium mb-1 mt-1">{children}</h3>,
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noreferrer" className="underline" style={{ color: "var(--c-indigo)" }}>{children}</a>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
