const C = {
  canvas:  "#0c0a09",
  surface: "#1a1917",
  raised:  "#242220",
  border:  "#292524",
  text:    "#f5f4f2",
  muted:   "#a6a09b",
  faint:   "#6b6460",
  indigo:  "#7c75ff",
  indigoGlow: "rgba(124,117,255,0.08)",
  indigoBorder: "rgba(124,117,255,0.35)",
  high:    "#ef4444",
  medium:  "#f59e0b",
  low:     "#22c55e",
} as const;

function Node({
  label, sub, accent = false, highlight = false, mono = false
}: {
  label: string; sub?: string; accent?: boolean; highlight?: boolean; mono?: boolean;
}) {
  return (
    <div
      className="rounded-xl px-4 py-3 flex-1 min-w-0"
      style={{
        background: highlight ? C.indigoGlow : C.surface,
        border: `1px solid ${highlight ? C.indigo : accent ? C.indigoBorder : C.border}`,
      }}
    >
      <div
        className="text-xs font-semibold"
        style={{
          color: highlight ? C.indigo : C.text,
          fontFamily: mono ? "ui-monospace, monospace" : "inherit",
        }}
      >
        {label}
      </div>
      {sub && (
        <div className="text-[10px] mt-0.5 leading-relaxed" style={{ color: C.faint, fontFamily: "ui-monospace, monospace" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function Arrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center my-2" style={{ gap: 0 }}>
      {label && (
        <span className="text-[10px] mb-1" style={{ color: C.faint, fontFamily: "ui-monospace, monospace", letterSpacing: "0.04em" }}>
          {label}
        </span>
      )}
      <svg width="2" height="24" viewBox="0 0 2 24">
        <line x1="1" y1="0" x2="1" y2="18" stroke={C.border} strokeWidth="1.5" />
        <polygon points="1,24 -2,17 4,17" fill={C.faint} />
      </svg>
    </div>
  );
}

function MultiArrow({ count }: { count: number }) {
  return (
    <div className="flex justify-around my-2">
      {Array.from({ length: count }).map((_, i) => (
        <svg key={i} width="2" height="24" viewBox="0 0 2 24">
          <line x1="1" y1="0" x2="1" y2="18" stroke={C.border} strokeWidth="1.5" />
          <polygon points="1,24 -2,17 4,17" fill={C.faint} />
        </svg>
      ))}
    </div>
  );
}

export function ArchDiagram() {
  return (
    <div
      className="rounded-2xl p-6 w-full"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <div
        className="text-[10px] font-semibold uppercase mb-5"
        style={{ color: C.faint, letterSpacing: "0.10em", fontFamily: "ui-monospace, monospace" }}
      >
        Data flow & architecture
      </div>

      {/* Layer 1: Inputs */}
      <div>
        <div className="text-[10px] mb-2" style={{ color: C.faint, fontFamily: "ui-monospace, monospace", letterSpacing: "0.04em" }}>
          INPUTS
        </div>
        <div className="flex gap-2">
          <Node label="Consumption data" sub="6 drugs × 5 countries · national DDD rates" />
          <Node label="Drug parameters" sub="PNEC · LOD · excretion fraction" />
          <Node label="105 sampling sites" sub="on real urban stream networks" />
          <Node label="OSM waterways" sub="Garonne · Schelde · Calore · Mondego · Akerselva" />
        </div>
      </div>

      <MultiArrow count={4} />

      {/* Layer 2: The Innovation */}
      <div
        className="rounded-xl p-4"
        style={{ background: C.indigoGlow, border: `1px solid ${C.indigo}` }}
      >
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <div
              className="text-[10px] font-semibold uppercase mb-1"
              style={{ color: C.indigo, fontFamily: "ui-monospace, monospace", letterSpacing: "0.10em" }}
            >
              ★ The innovation — untreated pathway
            </div>
            <div className="text-sm font-semibold mb-1" style={{ color: C.text }}>
              λ = leakage fraction · log-uniform(0.002, 0.15)
            </div>
            <div className="text-xs leading-relaxed" style={{ color: C.muted }}>
              Standard models (ePiE, GREAT-ER) set λ = 0 for all sites here — they only account for WWTP outfalls.
              PharmaShed models the drug load reaching streams via sewer leakage, misconnections, and combined overflows.
            </div>
          </div>
          <div
            className="rounded-lg px-3 py-2 text-center shrink-0"
            style={{ background: C.raised, border: `1px solid ${C.border}` }}
          >
            <div className="text-[10px]" style={{ color: C.faint, fontFamily: "ui-monospace, monospace" }}>ePiE / GREAT-ER</div>
            <div className="text-sm font-semibold mt-0.5" style={{ color: "#f87171" }}>PEC ≈ 0</div>
            <div className="text-[10px]" style={{ color: C.faint }}>for these streams</div>
          </div>
        </div>
      </div>

      <Arrow />

      {/* Layer 3: Monte Carlo Engine */}
      <div
        className="rounded-xl p-4"
        style={{ background: C.raised, border: `1px solid ${C.border}` }}
      >
        <div
          className="text-[10px] font-semibold uppercase mb-2"
          style={{ color: C.faint, fontFamily: "ui-monospace, monospace", letterSpacing: "0.04em" }}
        >
          Monte Carlo Engine
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <div className="rounded-lg px-3 py-2.5" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
            <div className="text-xs font-semibold mb-0.5" style={{ color: C.text }}>Draw parameters</div>
            <div className="text-[10px] leading-relaxed" style={{ color: C.faint, fontFamily: "ui-monospace, monospace" }}>
              λ ~ LogU(0.002, 0.15)<br />
              Q ~ LogU per size class<br />
              C ~ national data ± σ
            </div>
          </div>
          <div className="rounded-lg px-3 py-2.5" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
            <div className="text-xs font-semibold mb-0.5" style={{ color: C.text }}>Compute PEC</div>
            <div className="text-[10px] leading-relaxed" style={{ color: C.faint, fontFamily: "ui-monospace, monospace" }}>
              load = pop × C × λ<br />
              PEC = load / Q<br />
              RQ = PEC / PNEC
            </div>
          </div>
          <div className="rounded-lg px-3 py-2.5" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
            <div className="text-xs font-semibold mb-0.5" style={{ color: C.text }}>1,000 draws</div>
            <div className="text-[10px] leading-relaxed" style={{ color: C.faint, fontFamily: "ui-monospace, monospace" }}>
              per site × drug pair<br />
              105 sites × 6 drugs<br />
              = 630,000 draws total
            </div>
          </div>
        </div>
      </div>

      <Arrow />

      {/* Layer 4: Score */}
      <div
        className="rounded-xl p-4"
        style={{ background: C.raised, border: `1px solid ${C.border}` }}
      >
        <div
          className="text-[10px] font-semibold uppercase mb-2"
          style={{ color: C.faint, fontFamily: "ui-monospace, monospace", letterSpacing: "0.04em" }}
        >
          Sampling Priority Score
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="text-sm" style={{ color: C.muted }}>
            score = share of 1,000 draws with{" "}
            <span style={{ color: C.text, fontFamily: "ui-monospace, monospace" }}>RQ &gt; 1</span>
          </div>
          <div className="flex gap-2">
            {[
              { label: "High", threshold: "≥ 0.5", color: C.high },
              { label: "Medium", threshold: "≥ 0.1", color: C.medium },
              { label: "Low", threshold: "< 0.1", color: C.low },
            ].map((t) => (
              <div
                key={t.label}
                className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}
              >
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: t.color }} />
                <span className="text-xs" style={{ color: C.text }}>{t.label}</span>
                <span className="text-[10px]" style={{ color: C.faint, fontFamily: "ui-monospace, monospace" }}>{t.threshold}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <MultiArrow count={4} />

      {/* Layer 5: Outputs */}
      <div>
        <div className="text-[10px] mb-2" style={{ color: C.faint, fontFamily: "ui-monospace, monospace", letterSpacing: "0.04em" }}>
          OUTPUTS
        </div>
        <div className="flex gap-2">
          <Node label="Priority map" sub="5 cities · colored markers · city × drug filter" accent />
          <Node label="Scenario explorer" sub="adjust λ · Q · C · live score recompute" accent />
          <Node label="FHIR Bundles" sub="OneAquaHealth IG · Observation resources · HL7 R4" accent />
          <Node label="Consistency checks" sub="5 pre-registered checks vs Rodrigues 2025" accent />
        </div>
      </div>
    </div>
  );
}
