import { useStore } from "../../data/store";

const STEPS = [
  {
    n: "01",
    title: "Monte Carlo exposure model",
    body: "For each site × drug pair, 1,000 draws of uncertain parameters — leakage fraction (λ), river flow (Q), consumption (C) — produce a full distribution of predicted environmental concentrations (PEC). Every draw includes the untreated pathway that ePiE and GREAT-ER ignore.",
  },
  {
    n: "02",
    title: "Sampling priority score",
    body: "The score is the share of draws where PEC ÷ PNEC (the risk quotient) exceeds 1. High ≥ 0.5 · Medium ≥ 0.1 · Low < 0.1. It is an evidence-based screening index under stated priors — not a probability of exceedance, and it never labels a stream safe or unsafe.",
  },
  {
    n: "03",
    title: "Pre-registered consistency checks",
    body: "Five checks compare predicted detection shares, city rankings, and concentration ranges against Rodrigues et al. 2025 field data. Predictions are frozen before comparison, preventing post-hoc tuning. The checks demonstrate the validation pipeline — ready to run again the moment real parameters replace illustrative ones.",
  },
  {
    n: "04",
    title: "FHIR output aligned with OneAquaHealth IG",
    body: "Every prediction is exported as a FHIR Observation resource with the oneaquahealth-observation profile, category model-prediction, and components for PEC percentiles, RQ p50, sampling priority score, and LOD share. Results sit alongside real lab data in the same HAPI server, distinguishable by category and meta.tag.",
  },
];

const CITIES = [
  { id: "TLS", name: "Toulouse", country: "FR", flag: "🇫🇷", highlight: "hotspot city in paper" },
  { id: "GNT", name: "Ghent", country: "BE", flag: "🇧🇪", highlight: "highest paracetamol" },
  { id: "BNV", name: "Benevento", country: "IT", flag: "🇮🇹", highlight: "OAH IG example sites" },
  { id: "CBR", name: "Coimbra", country: "PT", flag: "🇵🇹", highlight: "lowest load city" },
  { id: "OSL", name: "Oslo", country: "NO", flag: "🇳🇴", highlight: "best dilution" },
];

const DRUGS = ["carbamazepine", "atenolol", "losartan", "irbesartan", "paracetamol", "citalopram"];

const CITATIONS = [
  {
    ref: "Rodrigues et al. 2025",
    title: "Occurrence and risk assessment of pharmaceuticals in urban streams across five European cities",
    journal: "Journal of Hazardous Materials",
    volume: "499:139946",
    note: "102 sites · 5 cities · 20 drugs · the observed dataset used for all consistency checks",
    href: "https://doi.org/10.1016/j.jhazmat.2025.139946",
  },
  {
    ref: "OneAquaHealth IG",
    title: "OneAquaHealth FHIR Implementation Guide",
    journal: "HL7 FHIR",
    volume: "v0.1.x",
    note: "Data standard for integrated environmental & health observations — PharmaShed outputs are IG-conformant",
    href: "https://oneaquahealth.org/fhir/",
  },
  {
    ref: "IEEE Hackathon 2026",
    title: "IEEE Global Humanitarian Technology Conference — OneAquaHealth Digital Health Hackathon",
    journal: "Track 7: Digital Health Standards (primary) · Track 6: Environmental Health",
    volume: "2026",
    note: "Competition context for this prototype",
    href: "https://oneaquahealth-ieee-hackathon.devpost.com",
  },
];

const OWN_DATA_STEPS = [
  {
    file: "drug_parameters.csv",
    desc: "Replace illustrative PNEC, LOD, and excretion fractions with values sourced from peer-reviewed ecotoxicology literature.",
  },
  {
    file: "consumption.csv",
    desc: "Replace illustrative consumption rates with country-specific DDD × population estimates from national pharmaceutical data.",
  },
  {
    file: "sites.geojson",
    desc: "Add your own stream sampling points with GPS coordinates, stream order, and population buffer. The auto-placement scripts can generate candidates from OSM waterway geometries.",
  },
];

export function HomeTab() {
  const setActiveTab = useStore((s) => s.setActiveTab);
  const results = useStore((s) => s.results);

  const siteCount = results?.results
    ? [...new Set(results.results.map((r) => r.site_id))].length
    : "—";

  return (
    <div className="overflow-y-auto h-full">
      {/* Hero */}
      <div className="relative bg-gradient-to-br from-blue-700 via-blue-600 to-blue-900 dark:from-blue-950 dark:via-blue-900 dark:to-neutral-950 text-white px-6 py-16 overflow-hidden">
        {/* subtle background texture */}
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{
          backgroundImage: "radial-gradient(circle at 20% 50%, white 0%, transparent 50%), radial-gradient(circle at 80% 20%, white 0%, transparent 40%)"
        }} />
        <div className="relative max-w-2xl mx-auto text-center">
          <a
            href="https://oneaquahealth-ieee-hackathon.devpost.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-white/15 hover:bg-white/25 transition-colors rounded-full px-4 py-1.5 text-sm mb-6 border border-white/20"
          >
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse inline-block" />
            IEEE OneAquaHealth Hackathon 2026 · Track 7
          </a>
          <h1 className="text-5xl font-extrabold mb-4 tracking-tight">PharmaShed</h1>
          <p className="text-xl text-blue-100 font-medium mb-3">
            Pharmaceutical sampling priority screening for urban streams
          </p>
          <p className="text-blue-200 text-sm max-w-xl mx-auto mb-10 leading-relaxed">
            Existing models (ePiE, GREAT-ER) predict near-zero pharmaceutical concentrations in streams without a treatment-plant outfall — missing the untreated pathway entirely. PharmaShed closes that gap with a Monte Carlo exposure model, pre-registered consistency checks, and FHIR output aligned with the OneAquaHealth Implementation Guide.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <button
              onClick={() => setActiveTab("explore")}
              className="px-7 py-3 bg-white text-blue-700 font-bold rounded-xl hover:bg-blue-50 transition-colors shadow-xl text-sm"
            >
              Explore the map →
            </button>
            <button
              onClick={() => setActiveTab("methodology")}
              className="px-7 py-3 bg-white/15 text-white font-medium rounded-xl hover:bg-white/25 transition-colors border border-white/30 text-sm"
            >
              Read the methodology
            </button>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="bg-neutral-50 dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-4xl mx-auto px-6 py-5 flex flex-wrap gap-10 justify-center">
          {[
            { n: siteCount.toString(), label: "sampling sites" },
            { n: "5", label: "European cities" },
            { n: "6", label: "pharmaceuticals" },
            { n: "1,000", label: "Monte Carlo draws per site × drug" },
            { n: "5", label: "pre-registered consistency checks" },
          ].map(({ n, label }) => (
            <div key={label} className="text-center">
              <div className="text-3xl font-extrabold text-blue-600 dark:text-blue-400">{n}</div>
              <div className="text-xs text-neutral-500 mt-0.5 max-w-[12ch] leading-tight">{label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-12 flex flex-col gap-14">

        {/* Problem */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-5">The gap we address</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              {
                icon: "🔍",
                heading: "Blind spot in existing models",
                body: "ePiE and GREAT-ER route drug loads through treatment-plant outfalls. Streams without one get predicted PEC ≈ 0 — even where sewer leakage, misconnections, and overflow events are the dominant source.",
              },
              {
                icon: "📊",
                heading: "91% detection at 102 field sites",
                body: "Rodrigues et al. 2025 sampled 102 urban stream sites across 5 European cities. At least one pharmaceutical was detected at 91% of sites; 79% had mixtures. Irbesartan peaked at 31,659 ng/L in Toulouse.",
              },
              {
                icon: "💡",
                heading: "Screening, not certainty",
                body: "PharmaShed tells water authorities which sites most warrant a sample, under stated assumptions. It is a decision-support tool that makes field monitoring budgets go further — not a substitute for measurement.",
              },
            ].map((p) => (
              <div
                key={p.heading}
                className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5 bg-white dark:bg-neutral-900 hover:border-blue-300 transition-colors"
              >
                <div className="text-3xl mb-3">{p.icon}</div>
                <h3 className="text-sm font-semibold mb-2">{p.heading}</h3>
                <p className="text-xs text-neutral-500 leading-relaxed">{p.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* How it works */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-5">How it works</h2>
          <div className="flex flex-col gap-0">
            {STEPS.map((s, i) => (
              <div key={s.n} className="flex gap-5">
                <div className="flex flex-col items-center">
                  <div className="w-10 h-10 rounded-full bg-blue-600 text-white text-sm font-bold flex items-center justify-center shrink-0 shadow-md">
                    {s.n}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className="w-px flex-1 bg-gradient-to-b from-blue-300 to-neutral-200 dark:from-blue-700 dark:to-neutral-700 my-1" />
                  )}
                </div>
                <div className="pb-8">
                  <h3 className="text-sm font-semibold mb-1.5 text-neutral-800 dark:text-neutral-100">{s.title}</h3>
                  <p className="text-xs text-neutral-500 leading-relaxed max-w-xl">{s.body}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Coverage */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-5">Coverage</h2>
          <div className="flex flex-wrap gap-3 mb-5">
            {CITIES.map((c) => (
              <div
                key={c.id}
                className="flex items-center gap-3 px-4 py-3 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900"
              >
                <span className="text-2xl">{c.flag}</span>
                <div>
                  <div className="text-sm font-semibold">{c.name}</div>
                  <div className="text-[10px] text-neutral-400">{c.id} · {c.highlight}</div>
                </div>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {DRUGS.map((d) => (
              <span
                key={d}
                className="px-3 py-1 text-xs rounded-full bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 font-medium"
              >
                {d}
              </span>
            ))}
          </div>
        </section>

        {/* Bring your own data */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-2">Using this for real deployments</h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-5 leading-relaxed">
            This prototype uses deliberately round <strong>illustrative</strong> values for drug parameters and consumption — the pipeline is complete and correct, but not yet sourced. To deploy PharmaShed for a real city or study, replace three files and re-run the engine:
          </p>
          <div className="flex flex-col gap-3">
            {OWN_DATA_STEPS.map((s, i) => (
              <div
                key={s.file}
                className="flex gap-4 items-start rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4"
              >
                <div className="w-7 h-7 rounded-lg bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-sm font-bold flex items-center justify-center shrink-0">
                  {i + 1}
                </div>
                <div>
                  <code className="text-xs font-mono text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 rounded">
                    {s.file}
                  </code>
                  <p className="text-xs text-neutral-500 mt-1.5 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-neutral-400 mt-4 leading-relaxed">
            Once parameters are sourced, every screen updates automatically: the band chart provenance buttons link to your evidence, the consistency checks re-run against the same frozen predictions, and every FHIR resource drops the <code className="bg-neutral-100 dark:bg-neutral-800 px-1 rounded">illustrative-parameter</code> tag. The footer changes from "illustrative" to "all cited".
          </p>
        </section>

        {/* Tab navigation cards */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-5">Explore the prototype</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              {
                tab: "explore" as const,
                icon: "🗺",
                title: "Explore",
                desc: "Interactive map: filter by city and drug, click a site to see its concentration band chart, sensitivity tornado, and draw histogram.",
              },
              {
                tab: "scenarios" as const,
                icon: "⚙",
                title: "Scenarios",
                desc: "Drag λ (leakage), Q (flow), and C (consumption) multipliers and watch the priority score recompute live over 1,000 stored draws.",
              },
              {
                tab: "consistency" as const,
                icon: "✓",
                title: "Consistency",
                desc: "Five pre-registered checks comparing predictions with Rodrigues et al. 2025 observed data — demonstrating the validation pipeline.",
              },
              {
                tab: "methodology" as const,
                icon: "📐",
                title: "Methodology",
                desc: "Full model pipeline, priors table with sourcing status, identifiability callout, and ablation comparison (population-only vs full model).",
              },
            ].map((item) => (
              <button
                key={item.tab}
                onClick={() => setActiveTab(item.tab)}
                className="text-left rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5 bg-white dark:bg-neutral-900 hover:border-blue-400 dark:hover:border-blue-600 hover:shadow-md transition-all group"
              >
                <div className="text-2xl mb-2">{item.icon}</div>
                <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  {item.title}
                </div>
                <div className="text-xs text-neutral-500 mt-1 leading-relaxed">{item.desc}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Citations */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-5">References</h2>
          <div className="flex flex-col gap-3">
            {CITATIONS.map((c) => (
              <div
                key={c.ref}
                className="rounded-xl border border-neutral-200 dark:border-neutral-700 p-4 bg-white dark:bg-neutral-900"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-mono text-blue-600 dark:text-blue-400 mb-1">{c.ref}</div>
                    <div className="text-sm font-medium text-neutral-800 dark:text-neutral-100 mb-1">{c.title}</div>
                    <div className="text-xs text-neutral-500">{c.journal} · {c.volume}</div>
                    <div className="text-xs text-neutral-400 mt-1">{c.note}</div>
                  </div>
                  <a
                    href={c.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 px-3 py-1.5 text-xs rounded-lg bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-700 dark:hover:text-blue-300 transition-colors border border-neutral-200 dark:border-neutral-700 font-medium"
                  >
                    Open →
                  </a>
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="text-xs text-neutral-400 pb-4 text-center leading-relaxed">
          Built for the{" "}
          <a
            href="https://oneaquahealth-ieee-hackathon.devpost.com"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-blue-600 transition-colors"
          >
            IEEE OneAquaHealth Digital Health Hackathon 2026
          </a>
          {" "}· Track 7: Digital Health Standards · Track 6: Environmental Health
        </div>
      </div>
    </div>
  );
}
