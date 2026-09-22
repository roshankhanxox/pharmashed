# PharmaShed

**Sampling-priority screening for pharmaceuticals in urban streams.**

A Monte Carlo risk tool that tells environmental officers which sites to sample first — before they leave the office. Built for the IEEE OneAquaHealth Global Hackathon 2026 (Track 7 Digital Health Standards).

**Live demo →** [pharmashed.roshankhan.me](https://pharmashed.roshankhan.me)

---

## The problem

Existing pharmaceutical screening models (ePiE, GREAT-ER) route all drug load through wastewater treatment plant outfalls. They work well when a WWTP sits on the stream you're studying.

Most urban streams don't have one.

A 2025 field study ([Rodrigues et al., J. Hazard. Mater. 499:139946](https://pubmed.ncbi.nlm.nih.gov/39489128/)) screened 102 urban stream sites across five European cities. Pharmaceuticals were detected at **91% of sites** — up to 31,659 ng/L of irbesartan in Toulouse. Not one site had a WWTP on the stream. Every established tool predicted concentration ≈ 0 at all of them.

PharmaShed fills that gap by modelling the **untreated pathway**: sewer leakage, misconnections, and combined sewer overflows that bypass treatment entirely.

---

## What it does

| Feature | Detail |
|---|---|
| **Priority map** | 105 sites across 5 cities, colour-coded high / medium / low by sampling priority score |
| **6 pharmaceuticals** | Carbamazepine, atenolol, losartan, irbesartan, paracetamol, citalopram |
| **Monte Carlo engine** | 1,000 draws per site × drug; samples λ (leakage fraction) and Q (flow) from stated priors |
| **Scenario explorer** | What-if sliders for drought, sewer repair, leakage hotspot — score recomputes live in-browser over stored draws |
| **Ablation comparison** | WWTP-only vs population-only vs full model, side by side |
| **Consistency checks** | 5 pre-registered checks against Rodrigues et al. 2025 field data |
| **FHIR R4 output** | Location + Observation bundles conforming to the OneAquaHealth IG profiles |
| **AI assistant** | Groq-backed, tool-use loop, numeric guard — can only cite numbers from live tool calls |

---

## How the model works

```
PEC = (population × DDD × λ) / Q
RQ  = PEC / PNEC
score = fraction of draws with RQ > 1
```

**λ (lambda)** — the untreated leakage fraction — is the core innovation. It is drawn from a log-uniform prior `(0.002, 0.15)` based on Fenz et al. 2005 and the APUSS project (city-wide exfiltration 0.5–3% of dry-weather flow; local hotspots up to 15%). The log scale covers that spread without over-weighting extremes.

**Q (river flow)** is placed directly as a prior per stream size class (small: 5–100 L/s, medium: 20–500 L/s) rather than sampled from width × depth × velocity, which produces physically impossible streams.

**Identifiability**: λ and Q appear only as a ratio in the PEC equation. A single grab sample cannot separate them — this is a fundamental mathematical constraint, not a data gap. PharmaShed propagates the joint prior uncertainty through every draw rather than hiding it behind a point estimate.

---

## Cities

| Code | City | Country |
|---|---|---|
| TLS | Toulouse | France |
| GNT | Ghent | Belgium |
| BNV | Benevento | Italy |
| CBR | Coimbra | Portugal |
| OSL | Oslo | Norway |

21 synthetic monitoring sites per city on real OpenStreetMap waterways.

---

## Stack

| Layer | Tool |
|---|---|
| Engine | Python 3.12, NumPy, SciPy — runs offline to generate `data/build/` |
| API | FastAPI (Render free tier) |
| Frontend | Vite + React + TypeScript strict, Zustand, MapLibre GL, hand-written SVG charts, Tailwind |
| Scenario math | Client-side Float32 arithmetic over precomputed draws — no server call on slider drag |
| FHIR | Static R4 bundles, `observation-with-component-oah` and `location-oah` OAH IG profiles |
| AI assistant | Groq (open-source LLM), tool-use loop, numeric guard |
| CI | Vercel (frontend) + Render (API) |

---

## FHIR interoperability

PharmaShed publishes every prediction as an HL7 FHIR R4 `Observation` resource conforming to the [OneAquaHealth Implementation Guide](https://github.com/hl7-eu/oah) (`observation-with-component-oah` profile). Each resource carries:

- PEC at p05 / p50 / p95 in ng/L
- RQ at p50
- Sampling priority score
- LOD share
- `category: model-prediction` — distinguishes model output from lab results on a shared server
- `meta.tag: illustrative-parameter` — drops when real sourced values replace placeholders

The FHIR tab co-hosts PharmaShed bundles alongside the OAH IG's own example resources (Benevento air quality, Almyros water chemistry), demonstrating the consortium's vision of a unified One Health FHIR server. A single query parameter — `Observation?category=model-prediction` — filters them apart.

---

## Parameters

All drug parameters and consumption values in the current prototype are **illustrative** — deliberately round numbers within a plausible order of magnitude, badged as such throughout the UI and in every FHIR resource.

The sourcing pipeline is built and ready. Replacing `drug_parameters.csv` and `consumption.csv` causes the engine to recompute 630,000 draws (105 sites × 6 drugs × 1,000), rebuild every chart, and regenerate every FHIR bundle. Nothing else changes.

---

## Local development

```bash
# Install dependencies
uv sync
cd web && pnpm install

# Start API + frontend together
./dev.sh
# API  → http://localhost:8000/docs
# Web  → http://localhost:5173

# Run tests
uv run pytest
cd web && pnpm tsc --noEmit
```

`dev.sh` sets `PHARMASHED_DATA=contracts/fixtures` so the API reads local fixture JSON — no live database needed.

### Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `GROQ_API_KEY` | API (Render dashboard) | Assistant LLM |
| `CORS_ORIGINS` | API | Allowed frontend origins |
| `PHARMASHED_DATA` | API | Path to data directory (defaults to `data/build/`) |
| `VITE_DATA_BASE` | Web `.env.production` | API base URL for deployed frontend |

---

## Repo layout

```
contracts/          JSON schemas + TypeScript types + test fixtures
data/
  params/           drug_parameters.csv, priors.yaml
  consumption/      consumption.csv
  observed/         Rodrigues 2025 field data — only engine/checks/ may read this
  build/            engine output (gitignored except fixtures)
engine/             Python Monte Carlo engine (M02–M14)
api/                FastAPI + assistant tools (M16–M17)
web/                Vite / React frontend (M18–M22)
fhir/               OAH IG terminology, validator script, generated bundles
infra/              docker-compose for local HAPI FHIR server
scripts/            fixture generation, type generation
```

---

## Validation

Five pre-registered consistency checks (C1–C5) run against predictions frozen before any comparison with the Rodrigues et al. 2025 field data:

| Check | What it tests |
|---|---|
| C1 | Detection share — fraction of sites above the detection limit |
| C2 | City rank order — does our ranking match TLS > GNT > BNV > CBR ≈ OSL? |
| C3 | Concentration order of magnitude — PEC bands within a factor of 10 of observed values |
| C4 | Cross-drug consistency — relative drug rankings hold across cities |
| C5 | Ablation stability — site rankings stay stable as model components are added |

Checks pass because the validation pipeline is structurally correct. Full validation against regulatory-grade results requires real sourced parameters.

---

## Citation

```bibtex
@article{rodrigues2025,
  author  = {Rodrigues et al.},
  title   = {Pharmaceuticals in urban streams: a European field study},
  journal = {Journal of Hazardous Materials},
  volume  = {499},
  pages   = {139946},
  year    = {2025},
  doi     = {10.1016/j.jhazmat.2025.139946}
}
```

---

## Never say

- "The stream is **safe**" or "**unsafe**" — say "the model estimates concentrations for priority-setting only"
- "**Probability** of harm" — say "share of simulated draws with RQ > 1 under stated priors"
- "**Validated**" — say "consistency checks pass; full validation requires real sourced parameters"
