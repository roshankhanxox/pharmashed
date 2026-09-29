/**
 * Home page for citizen view: plain language, no model jargon, clear next steps.
 * The expert home (index.tsx) keeps the technical story.
 */
import { useStore } from "../../data/store";
import { DEMO_NOTICE, SCORE_CAVEAT, TIER_LEGEND } from "../../data/copy";
import { Reveal } from "../../components/shell/Reveal";
import { AskBar } from "../../components/shell/AskBar";
import { useSmoothScroll } from "../../hooks/useSmoothScroll";

const TIER_COLOR = { high: "#ef4444", medium: "#f59e0b", low: "#22c55e" } as const;

const EXPLAINERS = [
  {
    title: "Medicines reach streams",
    body: "When we take medicine, some of it leaves our bodies and goes into the sewer. Leaking or overflowing sewers can carry it into nearby streams.",
  },
  {
    title: "Many streams are missed",
    body: "Older models only look at streams that sit next to a treatment plant. In a 2025 study of 102 urban stream sites in five European cities, medicines were found at 91% of them, and none had a treatment plant.",
  },
  {
    title: "A guide for where to test",
    body: "PharmaShed ranks places by how much a water sample there would teach us. It helps people and agencies decide where to look first.",
  },
];

const STEPS = [
  { n: "1", title: "Open the stream map", body: "Choose a city and a medicine." },
  { n: "2", title: "Tap a coloured dot", body: "See how high that spot ranks for testing, in plain words." },
  { n: "3", title: "Try “What if?”", body: "See how repairing a sewer or a dry spell would change the ranking." },
];

export function CitizenHome() {
  const setActiveTab = useStore((s) => s.setActiveTab);
  const setAudience = useStore((s) => s.setAudience);
  const results = useStore((s) => s.results);
  const scrollRef = useSmoothScroll();
  const siteCount = results ? new Set(results.results.map((r) => r.site_id)).size : 0;

  return (
    <div ref={scrollRef} className="overflow-y-auto h-full scrollbar-none" style={{ background: "var(--c-canvas)", color: "var(--c-text)" }}>
      {/* Hero */}
      <section className="px-8 pt-16 pb-12 max-w-4xl mx-auto">
        <Reveal>
          <h1
            className="font-display mb-5"
            style={{ fontSize: "clamp(40px, 5.5vw, 68px)", fontWeight: 400, lineHeight: 1.1 }}
          >
            Which streams should we <em style={{ fontStyle: "italic" }}>test</em> first?
          </h1>
        </Reveal>
        <Reveal delay={80}>
          <p className="text-lg mb-8 max-w-2xl leading-relaxed" style={{ color: "var(--c-muted)" }}>
            Medicines can end up in streams through leaking sewers. PharmaShed helps decide where to collect water samples first, so testing effort goes where it matters most.
          </p>
        </Reveal>
        <Reveal delay={160}>
          <div className="flex gap-3 flex-wrap items-center">
            <button
              onClick={() => setActiveTab("explore")}
              className="px-6 py-3 rounded-lg text-base font-semibold"
              style={{ background: "var(--c-accent)", color: "var(--c-on-accent)" }}
            >
              Open the stream map →
            </button>
          </div>
        </Reveal>
        <Reveal delay={240}>
          <div className="mt-8">
            <div className="text-sm font-medium mb-2" style={{ color: "var(--c-muted)" }}>Or just ask:</div>
            <AskBar />
          </div>
        </Reveal>
      </section>

      {/* Numbers */}
      <div style={{ borderTop: "1px solid var(--c-border)", borderBottom: "1px solid var(--c-border)", background: "var(--c-surface)" }}>
        <div className="max-w-4xl mx-auto flex">
          {[
            { n: siteCount ? String(siteCount) : "—", label: "places to look at" },
            { n: "5", label: "European cities" },
            { n: "6", label: "common medicines" },
          ].map(({ n, label }, i) => (
            <div key={label} className="flex-1 py-5 text-center" style={{ borderLeft: i > 0 ? "1px solid var(--c-border)" : "none" }}>
              <div className="text-3xl font-semibold" style={{ color: "var(--c-accent)" }}>{n}</div>
              <div className="text-sm mt-0.5" style={{ color: "var(--c-muted2)" }}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-8 py-14 flex flex-col gap-14">
        {/* Explainers */}
        <section>
          <Reveal><h2 className="text-2xl font-semibold mb-6">What is this about?</h2></Reveal>
          <div className="grid gap-4 sm:grid-cols-3">
            {EXPLAINERS.map((e, i) => (
              <Reveal key={e.title} delay={i * 90}>
                <div className="h-full rounded-xl p-5" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
                  <h3 className="font-semibold mb-2" style={{ fontSize: "1.0625rem" }}>{e.title}</h3>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--c-muted)" }}>{e.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* Steps */}
        <section>
          <Reveal><h2 className="text-2xl font-semibold mb-6">How to use it</h2></Reveal>
          <div className="flex flex-col gap-3">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 90}>
                <div className="flex gap-4 items-start rounded-xl p-4" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
                  <div
                    className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center font-semibold"
                    style={{ background: "var(--c-accent)", color: "var(--c-on-accent)" }}
                  >
                    {s.n}
                  </div>
                  <div>
                    <div className="font-semibold">{s.title}</div>
                    <div className="text-sm" style={{ color: "var(--c-muted)" }}>{s.body}</div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* Colour key + honesty */}
        <section>
          <Reveal>
            <div className="rounded-xl p-6" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
              <h2 className="text-xl font-semibold mb-4">What the colours mean</h2>
              <div className="flex gap-6 flex-wrap mb-4">
                {(["high", "medium", "low"] as const).map((t) => (
                  <span key={t} className="flex items-center gap-2 text-base">
                    <span className="inline-block w-4 h-4 rounded-full" style={{ background: TIER_COLOR[t] }} />
                    {TIER_LEGEND[t]}
                  </span>
                ))}
              </div>
              <p className="text-sm leading-relaxed mb-2" style={{ color: "var(--c-muted)" }}>{SCORE_CAVEAT}</p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--c-muted)" }}>{DEMO_NOTICE}</p>
            </div>
          </Reveal>
        </section>

        <Reveal>
          <p className="text-sm text-center pb-6" style={{ color: "var(--c-muted2)" }}>
            Want the model, the checks and the health-data standard behind this?{" "}
            <button onClick={() => setAudience("expert")} className="underline font-medium" style={{ color: "var(--c-accent)" }}>
              Switch to Expert view
            </button>
          </p>
        </Reveal>
      </div>
    </div>
  );
}
