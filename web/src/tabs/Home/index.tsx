import { useStore } from "../../data/store";
import { ArchDiagram } from "./ArchDiagram";
import { CitizenHome } from "./CitizenHome";
import { AskBar } from "../../components/shell/AskBar";
import { Reveal } from "../../components/shell/Reveal";
import { useSmoothScroll } from "../../hooks/useSmoothScroll";

/* ─── palette shorthands ─────────────────────────────────────────────────── */
const C = {
  canvas:  "var(--c-canvas)",
  surface: "var(--c-surface)",
  raised:  "var(--c-raised)",
  border:  "var(--c-border)",
  text:    "var(--c-text)",
  muted:   "var(--c-muted)",
  faint:   "var(--c-faint)",
  indigo:  "var(--c-indigo)",
  indigoDp:"var(--c-indigo-deep)",
} as const;

/* ─── data ───────────────────────────────────────────────────────────────── */
const CITIES = [
  { id: "TLS", name: "Toulouse",  flag: "🇫🇷", note: "highest drug load" },
  { id: "GNT", name: "Ghent",     flag: "🇧🇪", note: "highest paracetamol" },
  { id: "BNV", name: "Benevento", flag: "🇮🇹", note: "OAH IG example sites" },
  { id: "CBR", name: "Coimbra",   flag: "🇵🇹", note: "lowest load" },
  { id: "OSL", name: "Oslo",      flag: "🇳🇴", note: "best river dilution" },
];

const DRUGS = ["carbamazepine","atenolol","losartan","irbesartan","paracetamol","citalopram"];

const HOW_STEPS = [
  {
    n: "01",
    title: "Monte Carlo mass-balance",
    body: "1,000 draws of leakage fraction (λ), river flow (Q), and consumption (C) per site × drug produce a full distribution of predicted environmental concentrations (PEC) — including the untreated pathway that ePiE and GREAT-ER miss entirely.",
  },
  {
    n: "02",
    title: "Sampling priority score",
    body: "Score = share of draws where PEC ÷ PNEC exceeds 1. High ≥ 0.5 · Medium ≥ 0.1 · Low < 0.1. A screening index under stated priors — never a probability, never a safety verdict.",
  },
  {
    n: "03",
    title: "Pre-registered validation pipeline",
    body: "Five consistency checks compare predicted detection shares, city rankings, and concentration ranges against Rodrigues et al. 2025 field data. Predictions are frozen before any comparison — demonstrating an audit-ready pipeline.",
  },
  {
    n: "04",
    title: "FHIR output — OneAquaHealth IG",
    body: "Every prediction is an HL7 FHIR Observation resource with the oneaquahealth profile, category model-prediction, PEC percentile components, and an illustrative-parameter tag. A water authority and a hospital can query the same FHIR server and get both environmental predictions and patient prescriptions in a common format.",
  },
];

const OWN_DATA = [
  { file: "drug_parameters.csv", desc: "Replace illustrative PNEC, LOD, and excretion fractions with peer-reviewed ecotox values." },
  { file: "consumption.csv",     desc: "Replace illustrative consumption rates with country-specific DDD × population estimates." },
  { file: "sites.geojson",       desc: "Add GPS sampling points for your city. Auto-placement scripts generate candidates from OSM waterway geometries." },
];

const CITATIONS = [
  {
    ref: "Rodrigues et al. 2025",
    detail: "J. Hazard. Mater. 499:139946",
    note: "102 sites · 5 cities · 20 drugs — the observed dataset used for all consistency checks",
    href: "https://pubmed.ncbi.nlm.nih.gov/39489128/",
    doi: "10.1016/j.jhazmat.2025.139946",
  },
  {
    ref: "Oldenkamp et al. 2018",
    detail: "Environ. Sci. Technol. 52(21)",
    note: "ePiE model — WWTP-routed pharmaceutical exposure, the baseline PharmaShed extends with the untreated pathway",
    href: "https://doi.org/10.1021/acs.est.8b03862",
    doi: "10.1021/acs.est.8b03862",
  },
  {
    ref: "OneAquaHealth FHIR IG",
    detail: "HL7 FHIR · v0.1.x · hl7-eu/oah",
    note: "Data standard for integrated environmental & health observations — profile used for PharmaShed FHIR output",
    href: "https://github.com/hl7-eu/oah",
  },
  {
    ref: "IEEE Hackathon 2026",
    detail: "Track 7: Digital Health Standards",
    note: "IEEE OneAquaHealth Digital Health Hackathon — competition context",
    href: "https://oneaquahealth-ieee-hackathon.devpost.com",
  },
];

/* ─── sub-components ─────────────────────────────────────────────────────── */

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="text-xs uppercase tracking-widest mb-5"
      style={{ color: C.faint, letterSpacing: "0.06em" }}
    >
      {children}
    </p>
  );
}

function Divider() {
  return <hr style={{ borderColor: C.border, borderTopWidth: 1 }} className="my-12" />;
}

/* ─── main component ──────────────────────────────────────────────────────── */

function ExpertHome() {
  const setActiveTab = useStore((s) => s.setActiveTab);
  const scrollRef = useSmoothScroll();
  const results = useStore((s) => s.results);
  const siteCount = results
    ? [...new Set(results.results.map((r) => r.site_id))].length.toString()
    : "—";

  return (
    <div ref={scrollRef} className="overflow-y-auto h-full scrollbar-none" style={{ background: C.canvas, color: C.text }}>

      {/* ── HERO ──────────────────────────────────────────────────────────── */}
      <Reveal><section className="px-8 pt-20 pb-16 max-w-4xl mx-auto">

        {/* badge */}
        <a
          href="https://oneaquahealth-ieee-hackathon.devpost.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs mb-8 transition-opacity hover:opacity-70"
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            color: C.muted,
            letterSpacing: "0.04em",
          }}
        >
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: C.indigo }} />
          IEEE OneAquaHealth Hackathon 2026 · Track 7
        </a>

        {/* headline — Playfair Display with one italic word */}
        <h1
          className="font-display leading-tight mb-5"
          style={{
            fontFamily: "'Playfair Display', Georgia, serif",
            fontSize: "clamp(48px, 6vw, 80px)",
            fontWeight: 400,
            lineHeight: 1.1,
            color: C.text,
          }}
        >
          Know <em style={{ fontStyle: "italic" }}>where</em> to sample<br />
          before you go
        </h1>

        {/* sub */}
        <p className="text-lg mb-2 max-w-xl leading-relaxed" style={{ color: C.muted }}>
          PharmaShed screens for pharmaceutical contamination priority in urban streams using a Monte Carlo model that catches what ePiE and GREAT-ER miss.
        </p>
        <p className="text-sm mb-10 max-w-xl" style={{ color: C.faint }}>
          The untreated discharge pathway — sewer leakage, misconnections, overflows — is absent from standard models. At 91% of sampled sites, it matters.
        </p>

        {/* CTAs */}
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => setActiveTab("explore")}
            className="px-5 py-2.5 rounded-lg text-sm font-semibold transition-all"
            style={{ background: C.indigo, color: "#fff", letterSpacing: "0.02em" }}
            onMouseEnter={(e) => (e.currentTarget.style.background = C.indigoDp)}
            onMouseLeave={(e) => (e.currentTarget.style.background = C.indigo)}
          >
            Explore the map →
          </button>
          <button
            onClick={() => setActiveTab("methodology")}
            className="px-5 py-2.5 rounded-lg text-sm font-medium transition-all"
            style={{
              background: "transparent",
              border: `1px solid ${C.border}`,
              color: C.muted,
            }}
            onMouseEnter={(e) => { (e.currentTarget.style.borderColor = C.muted); }}
            onMouseLeave={(e) => { (e.currentTarget.style.borderColor = C.border); }}
          >
            Read methodology
          </button>
        </div>

        <div className="mt-8">
          <div className="text-sm font-medium mb-2" style={{ color: C.muted }}>Or ask the assistant:</div>
          <AskBar />
        </div>
      </section></Reveal>

      {/* ── STATS BAR ─────────────────────────────────────────────────────── */}
      <div style={{ borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}`, background: C.surface }}>
        <div
          className="max-w-4xl mx-auto flex"
          style={{ }}
        >
          {[
            { n: siteCount, label: "sampling sites" },
            { n: "5",       label: "European cities" },
            { n: "6",       label: "pharmaceuticals" },
            { n: "1,000",   label: "Monte Carlo draws" },
            { n: "5",       label: "consistency checks" },
          ].map(({ n, label }, i) => (
            <div
              key={label}
              className="flex-1 py-5 text-center"
              style={{ borderLeft: i > 0 ? `1px solid ${C.border}` : "none" }}
            >
              <div className="text-2xl font-semibold" style={{ color: C.indigo }}>{n}</div>
              <div className="text-xs mt-0.5" style={{ color: C.faint, letterSpacing: "0.02em" }}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-8 py-14 flex flex-col gap-0">

        {/* ── THE GAP ──────────────────────────────────────────────────────── */}
        <Reveal><section>
          <Eyebrow>The problem</Eyebrow>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              {
                icon: "◎",
                title: "Blind spot in standard models",
                body: "ePiE and GREAT-ER route drug loads via treatment-plant outfalls. Streams without one get predicted PEC ≈ 0 — even where leakage and overflows dominate.",
              },
              {
                icon: "◉",
                title: "91% detection in the field",
                body: "Rodrigues et al. 2025 sampled 102 sites across five European cities. At least one pharmaceutical was detected at 91% of sites; 79% had mixtures.",
              },
              {
                icon: "◈",
                title: "Screening, not certainty",
                body: "PharmaShed identifies which sites most warrant a sample under stated priors — a decision-support tool that makes monitoring budgets go further.",
              },
            ].map((p) => (
              <div
                key={p.title}
                className="rounded-xl p-5"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}
              >
                <div
                  className="text-xl mb-3"
                  style={{ color: C.indigo }}
                >
                  {p.icon}
                </div>
                <h3 className="text-sm font-semibold mb-2" style={{ color: C.text }}>
                  {p.title}
                </h3>
                <p className="text-xs leading-relaxed" style={{ color: C.muted }}>
                  {p.body}
                </p>
              </div>
            ))}
          </div>
        </section></Reveal>

        <Divider />

        {/* ── HOW IT WORKS ─────────────────────────────────────────────────── */}
        <Reveal><section>
          <Eyebrow>How it works</Eyebrow>
          <div className="flex flex-col">
            {HOW_STEPS.map((s, i) => (
              <div key={s.n} className="flex gap-5">
                <div className="flex flex-col items-center shrink-0">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold shrink-0"
                    style={{
                      background: C.surface,
                      border: `1px solid ${C.indigo}`,
                      color: C.indigo,
                    }}
                  >
                    {s.n}
                  </div>
                  {i < HOW_STEPS.length - 1 && (
                    <div
                      className="w-px flex-1 my-1"
                      style={{ background: C.border }}
                    />
                  )}
                </div>
                <div className="pb-8 pt-1.5">
                  <h3 className="text-sm font-semibold mb-1.5" style={{ color: C.text }}>
                    {s.title}
                  </h3>
                  <p className="text-xs leading-relaxed max-w-xl" style={{ color: C.muted }}>
                    {s.body}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section></Reveal>

        <Divider />

        {/* ── ARCHITECTURE ─────────────────────────────────────────────────── */}
        <Reveal><section>
          <Eyebrow>Architecture & data flow</Eyebrow>
          <ArchDiagram />
        </section></Reveal>

        <Divider />

        {/* ── COVERAGE ─────────────────────────────────────────────────────── */}
        <Reveal><section>
          <Eyebrow>Coverage</Eyebrow>
          <div className="flex flex-wrap gap-2 mb-5">
            {CITIES.map((c) => (
              <div
                key={c.id}
                className="flex items-center gap-3 px-4 py-3 rounded-xl"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}
              >
                <span className="text-xl">{c.flag}</span>
                <div>
                  <div className="text-sm font-medium" style={{ color: C.text }}>{c.name}</div>
                  <div
                    className="text-xs"
                    style={{ color: C.faint }}
                  >
                    {c.id} · {c.note}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {DRUGS.map((d) => (
              <span
                key={d}
                className="px-3 py-1 text-xs rounded-full"
                style={{
                  background: C.surface,
                  border: `1px solid ${C.border}`,
                  color: C.muted,
                  letterSpacing: "0.02em",
                }}
              >
                {d}
              </span>
            ))}
          </div>
        </section></Reveal>

        <Divider />

        {/* ── BRING YOUR DATA ───────────────────────────────────────────────── */}
        <Reveal><section>
          <Eyebrow>Deploying with real data</Eyebrow>
          <div
            className="rounded-xl p-5 mb-5"
            style={{ background: C.surface, border: `1px solid ${C.border}` }}
          >
            <p className="text-sm leading-relaxed" style={{ color: C.muted }}>
              This prototype uses deliberately round <strong style={{ color: C.text }}>illustrative</strong> values — the pipeline is complete and audit-ready, but parameters are not yet sourced. To run PharmaShed for a real city, replace three files and re-run the engine:
            </p>
          </div>
          <div className="flex flex-col gap-2">
            {OWN_DATA.map((s, i) => (
              <div
                key={s.file}
                className="flex gap-4 items-start rounded-xl p-4"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}
              >
                <span
                  className="w-6 h-6 rounded-md flex items-center justify-center text-xs font-semibold shrink-0"
                  style={{ background: C.raised, color: C.indigo }}
                >
                  {i + 1}
                </span>
                <div>
                  <code
                    className="text-xs px-2 py-0.5 rounded"
                    style={{ background: C.raised, color: C.indigo }}
                  >
                    {s.file}
                  </code>
                  <p className="text-xs mt-1.5 leading-relaxed" style={{ color: C.muted }}>
                    {s.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs mt-4 leading-relaxed" style={{ color: C.faint }}>
            Once parameters are sourced, every screen updates automatically — the consistency checks re-run, FHIR resources drop the{" "}
            <code
              className="px-1 py-0.5 rounded text-xs"
              style={{ background: C.raised, color: C.muted }}
            >
              illustrative-parameter
            </code>{" "}
            tag, and the footer switches from "illustrative" to "all cited".
          </p>
        </section></Reveal>

        <Divider />

        {/* ── EXPLORE THE APP ───────────────────────────────────────────────── */}
        <Reveal><section>
          <Eyebrow>Explore the prototype</Eyebrow>
          <div className="grid gap-3 sm:grid-cols-2">
            {([
              { tab: "explore",     icon: "MAP",  title: "Explore",     desc: "Interactive map — city × drug filtering, coloured site markers, concentration band chart, sensitivity tornado." },
              { tab: "scenarios",   icon: "SCN",  title: "Scenarios",   desc: "Drag λ · Q · C multipliers. Watch the priority score recompute live over 1,000 stored Monte Carlo draws." },
              { tab: "consistency", icon: "CHK",  title: "Consistency", desc: "Five pre-registered checks against Rodrigues et al. 2025 observed data — the validation pipeline, demonstrated." },
              { tab: "methodology", icon: "DOC",  title: "Methodology", desc: "Full model pipeline, priors table with sourcing status, identifiability callout, and ablation comparison." },
            ] as const).map((item) => (
              <button
                key={item.tab}
                onClick={() => setActiveTab(item.tab)}
                className="text-left rounded-xl p-5 transition-all group"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = C.indigo; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = C.border; }}
              >
                <div
                  className="text-xs font-semibold mb-2 tracking-widest"
                  style={{ color: C.faint }}
                >
                  {item.icon}
                </div>
                <div className="text-sm font-semibold mb-1" style={{ color: C.text }}>
                  {item.title}
                </div>
                <div className="text-xs leading-relaxed" style={{ color: C.muted }}>
                  {item.desc}
                </div>
                <div
                  className="text-xs mt-3 transition-opacity opacity-0 group-hover:opacity-100"
                  style={{ color: C.indigo }}
                >
                  Open →
                </div>
              </button>
            ))}
          </div>
        </section></Reveal>

        <Divider />

        {/* ── REFERENCES ───────────────────────────────────────────────────── */}
        <Reveal><section>
          <Eyebrow>References</Eyebrow>
          <div className="flex flex-col gap-3">
            {CITATIONS.map((c) => (
              <div
                key={c.ref}
                className="flex items-start justify-between gap-4 rounded-xl p-4"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}
              >
                <div className="flex-1 min-w-0">
                  <div
                    className="text-xs mb-1"
                    style={{ color: C.indigo }}
                  >
                    {c.ref}
                  </div>
                  <div className="text-sm font-medium mb-0.5" style={{ color: C.text }}>{c.detail}</div>
                  <div className="text-xs mb-1" style={{ color: C.faint }}>{c.note}</div>
                  {"doi" in c && c.doi && (
                    <div
                      className="text-xs"
                      style={{ color: C.faint }}
                    >
                      doi:{c.doi}
                    </div>
                  )}
                </div>
                <a
                  href={c.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 px-3 py-1.5 text-xs rounded-lg transition-colors"
                  style={{
                    background: C.raised,
                    border: `1px solid ${C.border}`,
                    color: C.muted,
                    textDecoration: "none",
                    letterSpacing: "0.04em",
                  }}
                  onMouseEnter={(e) => { (e.currentTarget.style.color = C.indigo); (e.currentTarget.style.borderColor = C.indigo); }}
                  onMouseLeave={(e) => { (e.currentTarget.style.color = C.muted); (e.currentTarget.style.borderColor = C.border); }}
                >
                  OPEN →
                </a>
              </div>
            ))}
          </div>
        </section></Reveal>

        <div className="text-xs text-center pb-4 mt-8" style={{ color: C.faint }}>
          PHARMASHED · IEEE ONEAQUAHEALTH HACKATHON 2026
        </div>
      </div>
    </div>
  );
}

/** Home tab: plain-language page for citizens, the technical story for experts. */
export function HomeTab() {
  const audience = useStore((s) => s.audience);
  return audience === "citizen" ? <CitizenHome /> : <ExpertHome />;
}
