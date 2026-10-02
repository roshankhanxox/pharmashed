# PharmaShed

**Sampling-priority screening for pharmaceuticals in urban streams.**

A Monte Carlo risk tool that tells environmental officers which sites to sample first — before they leave the office. Built for the IEEE OneAquaHealth Global Hackathon 2026 (Track 7 Digital Health Standards).

**Live demo →** [pharmashed.roshankhan.me](https://pharmashed.roshankhan.me)

---

## The problem

Existing pharmaceutical screening models (ePiE, GREAT-ER) route all drug load through wastewater treatment plant outfalls. They work well when a WWTP sits on the stream you're studying.

Most urban streams don't have one.

A 2025 field study ([Rodrigues et al., *J. Hazard. Mater.* 499:139946](https://doi.org/10.1016/j.jhazmat.2025.139946)) screened 102 urban stream sites across five European cities. Pharmaceuticals were detected at **91% of sites** — up to 31,659 ng/L of irbesartan in Toulouse. A model that routes drug load only through treatment-plant outfalls has nothing to say about a stream without one: it predicts concentration ≈ 0 there (our WWTP-only ablation shows this blind spot).

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
| **AI assistant** | OpenAI `gpt-5-mini` (Groq fallback), tool-use loop, numeric guard, usage limits — can only cite numbers from live tool calls |

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
| AI assistant | OpenAI `gpt-5-mini` (Groq fallback), tool-use loop, numeric guard |
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

**Validation.** All eleven bundles (105 Locations, 630 predictions, consumption, reference measurements, terminology, unverified citizen observations, and the IG's own examples) were checked with the official HL7 FHIR validator (6.10.4, FHIR R4) against the OneAquaHealth profiles: **0 errors, 1,530 warnings**. The warnings are best-practice notes (resources without narrative text, and our observation codes not being in the guide's suggested value set); none are conformance errors. The guide is published only as FSH source, so `scripts/validate_fhir.py` compiles it with SUSHI at a pinned commit (`hl7-eu/oah@b907cf0`) before validating. What this shows is that the *shape* of the output is valid; it says nothing about whether the numbers inside are right (the inputs are illustrative). A local HAPI FHIR server (`docker compose`) has not been run. To reproduce: `uv run pharmashed fhir && uv run python scripts/validate_fhir.py` (needs Java and Node; downloads about 200 MB the first time).

The FHIR tab co-hosts PharmaShed bundles alongside the OAH IG's own example resources (Benevento air quality, Almyros water chemistry), demonstrating the consortium's vision of a unified One Health FHIR server. A single query parameter — `Observation?category=model-prediction` — filters them apart.

---

## Parameters

All drug parameters and consumption values in the current prototype are **illustrative** — deliberately round numbers within a plausible order of magnitude, badged as such throughout the UI and in every FHIR resource.

The sourcing pipeline is built and ready. Replacing `drug_parameters.csv` and `consumption.csv` causes the engine to recompute 630,000 draws (105 sites × 6 drugs × 1,000), rebuild every chart, and regenerate every FHIR bundle. Nothing else changes.

---

## Reproducing the data

The numbers in the app come from the engine, not from hand-made fixtures. Inputs are still **illustrative** (see Parameters below); populations are real (GHS-POP R2023A, 500 m buffers).

```bash
uv run python scripts/fetch_ghspop.py --download   # 4 population tiles, about 200 MB, into data/raw/ (git-ignored)
uv run pharmashed population compute                # writes real populations into data/sites/sites.geojson
uv run python scripts/fill_illustrative.py          # only fills rows that are still todo
uv run pharmashed build                             # model run into data/build/, FHIR bundles into fhir/out/
uv run pharmashed freeze                            # strict run, git commit and tag (needs a clean tree)
uv run pharmashed checks                            # consistency checks C1-C5 against the frozen run
uv run python scripts/make_release.py               # committed snapshot in data/release/ that the deployed API serves
```

The API reads `data/build/` when it exists (local development) and falls back to `data/release/` (a deployed server, where the git-ignored build folder is absent). `PHARMASHED_DATA` overrides both.

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
| `OPENAI_API_KEY` | API (Render dashboard) | Assistant LLM (`GROQ_API_KEY` is an optional fallback) |
| `CORS_ORIGINS` | API | Allowed frontend origins |
| `PHARMASHED_DATA` | API | Path to data directory (defaults to `data/build/`, else `data/release/`) |
| `VITE_DATA_BASE` | Web `.env.production` | API base URL for deployed frontend |
| `DATABASE_URL` | API | Neon Postgres connection string (use the pooled one). Optional: without it the citizen-reports endpoints answer 503 and the rest of the API is unaffected |
| `NEON_AUTH_BASE_URL` | API | Neon Auth URL; the API verifies sign-in tokens against `<url>/.well-known/jwks.json` |
| `ADMIN_EMAILS` | API | Comma-separated emails treated as moderators. The email must also be **verified**, so turn on email verification in the Neon Auth settings first, or nobody can moderate |
| `AWS_ENDPOINT_URL_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`, `AWS_REGION` | API | Neon storage bucket (S3-compatible, private) for report photos. Optional: without them the photo button is hidden and nothing else changes |
| `VITE_NEON_AUTH_URL` | Web | The same Neon Auth URL; without it the sign-in controls are hidden |
| `VITE_NEON_AUTH_GOOGLE` | Web | Set to `true` to show "Continue with Google" (only if enabled in the Neon Auth project) |

**Citizen reports** (S5): signed-in people file a checklist report about a stream, optionally tidied by AI and with a photo; reports show as an unverified layer on the map and never change a score. Points, badges, a weekly challenge and a leaderboard reward useful reports; readers can flag reports, a moderator approves or hides held and flagged ones, people can delete their account, and approved reports are also served as unverified FHIR (`/api/fhir/citizen-observations`). Design and rules: [docs/S5-citizen-reports-plan.md](docs/S5-citizen-reports-plan.md).

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

## Citation and credits

The field data and the consistency checks come from this paper; please cite it:

```bibtex
@article{rodrigues2025,
  author  = {Rodrigues, Fernanda and Calapez, Ana R. and Pereira, Andr{\'e} M. P. T. and Silva, Liliana J. G. and Freitas, Andreia and Bouchali, Rayan and De Cock, Andree and Forio, Marie Anne Eurie and Goethals, Peter and Henni, Silje H. and Loyau, Adeline and Moen, Anne and Piscopo, Nadia and Schmeller, Dirk S. and da Silva, Janine P. and Dur{\~a}es, Luisa and Sim{\~o}es, Nuno E. C. and Feio, Maria J.},
  title   = {Patterns of pharmaceutical contamination in streams of European cities across urbanisation gradients: Potential impacts on One Health},
  journal = {Journal of Hazardous Materials},
  volume  = {499},
  pages   = {139946},
  year    = {2025},
  doi     = {10.1016/j.jhazmat.2025.139946}
}
```

How the model is built on other people's work:

- **Exposure model structure.** The WWTP-routed baseline is the ePiE model: Oldenkamp, Hoeks, Čengić, Barbarossa, et al., *Environ. Sci. Technol.* 52(21):12494–12503 (2018), [doi:10.1021/acs.est.8b03862](https://doi.org/10.1021/acs.est.8b03862). GREAT-ER is named as a comparison; its primary citation is not yet verified here.
- **Leakage (λ) prior.** Informed by Fenz, Blaschke, Clara, Kroiss, Mascher, Zessner, *Water Sci. Technol.* 52(9):209–217 (2005), [doi:10.2166/wst.2005.0321](https://doi.org/10.2166/wst.2005.0321), and the APUSS project. The prior itself (log-uniform 0.002–0.15) is our own stated assumption.
- **Population.** GHS-POP R2023A (Global Human Settlement Layer, European Commission Joint Research Centre), 500 m buffers.
- **Streams and basemap.** © OpenStreetMap contributors.
- **Data standard.** HL7 FHIR R4 and the OneAquaHealth Implementation Guide (hl7-eu/oah), validated with the HL7 validator.
- **Context.** Built for the IEEE OneAquaHealth Global Hackathon 2026, Track 7 (Digital Health Standards).

The drug parameters in this prototype are illustrative placeholders, not values from these papers.

---

## Never say

- "The stream is **safe**" or "**unsafe**" — say "the model estimates concentrations for priority-setting only"
- "**Probability** of harm" — say "share of simulated draws with RQ > 1 under stated priors"
- "**Validated**" — say "consistency checks pass; full validation requires real sourced parameters"
