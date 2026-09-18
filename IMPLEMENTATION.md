# PharmaShed — Implementation Plan

Monorepo build spec. Every module has an ID (`M00`–`M24`) and a heading `## Mxx`, so a coding session can load only the section it needs:

```bash
grep -n "^## M" IMPLEMENTATION.md          # list modules with line numbers
sed -n '/^## M07/,/^## M08/p' IMPLEMENTATION.md   # print one module
```

Precedence when documents disagree: **CONTEXT.md decisions log > this file > docs/PharmaShed.md (concept v0.2)**.

---

## Part A — Shared foundations

### A1. Repository layout

```
pharmashed/
├── CONTEXT.md                 # session brief (read first, every session)
├── CHECKPOINT.md              # progress log (read second, update last)
├── IMPLEMENTATION.md          # this file
├── README.md
├── Makefile                   # all entry points
├── docs/
│   ├── PharmaShed.md          # concept doc v0.2
│   ├── demo-script.md         # M24
│   └── sources.md             # bibliography (R1–R25+)
├── contracts/                 # M01 — the single source of truth for data shapes
│   ├── schemas/*.schema.json
│   └── fixtures/*.json|.bin
├── data/
│   ├── params/
│   │   ├── drug_parameters.csv     # M02 (human-sourced, cited)
│   │   └── priors.yaml             # M02 (λ, Q classes, τ, C spread)
│   ├── consumption/consumption.csv # M03 (human-sourced, cited)
│   ├── sites/sites.geojson         # M04 (hand-placed)
│   ├── sites/streams.geojson       # M04 (OSM extract)
│   ├── observed/observed_rodrigues2025.csv  # evaluation only
│   ├── raw/                        # gitignored downloads (GHS-POP tiles)
│   ├── build/                      # engine outputs (gitignored except demo copy)
│   └── frozen/                     # M11 freeze output (committed + tagged)
├── engine/                    # Python package `pharmashed` (M02–M12)
│   ├── pyproject.toml
│   ├── src/pharmashed/
│   │   ├── config.py
│   │   ├── params.py          # M02
│   │   ├── consumption.py     # M03
│   │   ├── sites.py           # M04
│   │   ├── population.py      # M05
│   │   ├── priors.py          # M06
│   │   ├── model.py           # M07
│   │   ├── montecarlo.py      # M08
│   │   ├── sensitivity.py     # M09
│   │   ├── scoring.py         # M10
│   │   ├── export.py          # M11
│   │   ├── freeze.py          # M11
│   │   ├── checks/            # M12 (separate subpackage, own import rules)
│   │   ├── fhir/              # M13–M14
│   │   └── cli.py
│   └── tests/
├── fhir/                      # M13, M15
│   ├── terminology/           # CodeSystem + ValueSet JSON
│   ├── validator/             # validate.sh, downloaded jar (gitignored)
│   └── out/                   # generated bundles (gitignored; demo copy in data/build)
├── api/                       # M16–M17 FastAPI app
│   ├── pyproject.toml
│   └── src/pharmashed_api/
│       ├── main.py
│       ├── routes/
│       └── assistant/
├── web/                       # M18–M22 Vite + React + TS
│   ├── package.json
│   └── src/
├── infra/docker-compose.yml   # M15 HAPI FHIR + api
├── scripts/                   # one-off data helpers
└── .github/workflows/ci.yml   # M23
```

### A2. Toolchain

| Area | Choice | Why |
|---|---|---|
| Python | 3.12, `uv` workspaces (`engine`, `api`) | fast, one lockfile |
| Numerics | numpy, scipy (stats), pandas | vectorised Monte Carlo |
| Geo | geopandas, shapely, rasterio, pyproj | buffers + raster sampling |
| Validation of data files | pydantic v2 | typed loaders with good errors |
| FHIR building | `fhir.resources` (R4B/R5 models) | stays in Python; Java only for validator |
| FHIR validation | HL7 FHIR Validator CLI (Java 17) | official tool |
| FHIR server | HAPI FHIR JPA (Docker image) | local demo only |
| API | FastAPI + uvicorn | |
| LLM | Anthropic Messages API with tool use | model string via env |
| Web | Vite, React 18, TypeScript, Zustand, MapLibre GL JS, Tailwind CSS | no SSR needed |
| Charts | hand-written SVG components | full control, tiny bundle |
| Types across stack | JSON Schema → `json-schema-to-typescript` (web) and pydantic models (python) | one contract |
| Tests | pytest, vitest | |
| Lint | ruff, eslint, prettier | |

Optional Java path: the FHIR builder (M14) may be rewritten in Java with the HAPI FHIR structures library if the owner prefers. The contract (input `results.json`, output bundles) stays identical, so nothing else changes. Default: Python.

### A3. Makefile targets (entry points)

```
make setup          # uv sync, pnpm install, download validator jar
make fixtures       # regenerate contracts/fixtures from schemas (M01)
make data-check     # validate params, priors, consumption, sites (M02–M04)
make run            # engine run, dev mode → data/build/ (M08–M11)
make run-strict     # engine run, fails on any unsourced parameter
make freeze         # strict run → data/frozen/ + git tag (M11)
make checks         # consistency checks against frozen predictions (M12)
make fhir           # build bundles (M14)
make fhir-validate  # run HL7 validator (M15)
make hapi-up        # docker-compose up HAPI, load bundles (M15)
make api            # run FastAPI (M16)
make web            # vite dev server (M18)
make eval-assistant # assistant eval set (M17)
make test           # all python + web tests
make demo-build     # copy build artefacts into web/public/data for static hosting
```

### A4. Model equations (single reference — modules point here)

Indices: site *s*, drug *d*, country *c* (country of the site's city), draw *i*.

```
L[s,d]   = P[s] · C[c,d] · DDD[d] / 1000                     # g/day consumed near site
E[s,d]   = L[s,d] · fe[d]                                     # g/day excreted as parent
M[s,d]   = E[s,d] · ( λ[s] + w[s]·(1−λ[s])·(1−R[d]) )         # g/day into stream
Qd[s]    = Q[s] · 86400 · 1000                                # m³/s → L/day
PEC[s,d] = M[s,d] / Qd[s] · exp(−k[d]·τ[s]) · 1e9            # ng/L
RQ[s,d]  = PEC[s,d] / PNEC[d]
score[s,d] = mean_i( RQ[s,d,i] > 1 )                          # sampling priority score
lodShare[s,d] = mean_i( PEC[s,d,i] > LOD[d] )
```

Rules:
- `w[s] = 0` for every MVP site (no WWTP outfall). With w=0, all scenario overrides on λ, Q, C are **exact multiplicative rescalings of RQ**: `RQ' = RQ · mλ · mC / mQ`. The web client relies on this (M20). If any site ever has w=1, the client must fall back to the API scenario endpoint for that site.
- Units: P in persons, C in DDD/1000 inhabitants/day, DDD in g, Q in m³/s, k in 1/h, τ in h, PNEC and LOD in ng/L.
- Model variants (M07) for ablation: `full`, `wwtp_only` (λ=0 → PEC=0 for w=0 sites, i.e. the ePiE-like blind spot), `pop_only` (C set to the cross-country mean, per drug).

### A5. Global conventions

- **Seeded RNG everywhere** (`numpy.random.default_rng(seed)`); seed in `config.py` and in `results.meta`.
- **Draw counts:** `N_DRAWS = 10_000` for statistics; `N_STORED = 1_000` stored per site–drug for the client (first 1,000 of the same draws, so they are consistent).
- **IDs:** site ids `{CITY3}-{NN}` (e.g. `TLS-03`), drugs lowercase INN (`irbesartan`, `paracetamol`), parameters `snake_case`.
- **Never** read `data/observed/` outside `engine/src/pharmashed/checks/`. Enforced by a test (M12).
- **Never** put a number in `drug_parameters.csv` or `consumption.csv` without `source_url` and `source_note`. Enforced by M02/M03 loaders.
- **Dev mode vs strict mode:** dev mode allows rows with `status=todo` using clearly fake placeholder values from `contracts/fixtures/dev_placeholders.yaml`, and sets `meta.dev_placeholders=true`. The UI shows a red banner when that flag is set. Strict mode refuses to run on any `todo` row. Freeze requires strict.
- Every build artefact carries `meta.engine_version` (from package version) and `meta.generated_at`.

---

## Part B — Modules

Each module lists: **Path · Depends on · Purpose · Inputs · Outputs · Build · Acceptance.** "Acceptance" items are what CHECKPOINT.md ticks.

---

## M00 — Repo scaffold and tooling

**Path:** root · **Depends on:** — · **Owner hint:** easy, first session.

**Purpose:** empty-but-working skeleton so every later module drops into place.

**Build:**
1. Create the layout in A1 with placeholder `__init__.py`, `package.json`, etc.
2. `uv` workspace: root `pyproject.toml` declaring members `engine`, `api`.
3. `web/`: `pnpm create vite web --template react-ts`, add Tailwind, MapLibre, Zustand, vitest.
4. `Makefile` with every target from A3 (targets not yet implemented print `TODO Mxx`).
5. `.gitignore`: `data/raw/`, `data/build/`, `fhir/out/`, `fhir/validator/*.jar`, `node_modules`, `.venv`, `.env`.
6. `.env.example`: `ANTHROPIC_API_KEY=`, `ASSISTANT_MODEL=claude-sonnet-5`, `HAPI_BASE=http://localhost:8080/fhir`.
7. ruff + eslint + prettier configs; pre-commit optional.
8. Copy `PharmaShed.md` into `docs/`, `observed_rodrigues2025.csv` into `data/observed/`.

**Acceptance:** `make setup && make test` succeeds (zero tests is fine); `make web` serves the Vite page.

---

## M01 — Contracts: JSON Schemas, fixtures, generated types

**Path:** `contracts/` · **Depends on:** M00 · **Critical:** frontend and engine both build against this from day one.

**Purpose:** freeze data shapes so web and engine can develop in parallel.

**Files:**

| Schema | Describes |
|---|---|
| `sites.schema.json` | `sites.json` |
| `results.schema.json` | `results.json` |
| `draws.schema.json` | `draws_index.json` (the binary layout) |
| `checks.schema.json` | `checks.json` (M12 output) |
| `methodology.schema.json` | `methodology.json` (priors table, model stages, ablation rankings) |
| `provenance.schema.json` | `provenance.json` (keyed lookup for every ⓘ in the UI) |
| `fhir_index.schema.json` | `fhir_index.json` (resource list + query-demo counts + validator status) |

**`sites.json`**
```json
{
  "meta": { "generated_at": "…", "synthetic": true },
  "cities": [
    { "id": "TLS", "name": "Toulouse", "country": "FR", "center": [1.4442, 43.6047], "zoom": 12 }
  ],
  "sites": [
    {
      "id": "TLS-03", "city": "TLS", "name": "Synthetic site on <stream name>",
      "lonlat": [1.43, 43.61], "synthetic": true,
      "size_class": "M", "w": 0, "valid": true,
      "population_buffer": 5231, "population_source_key": "pop:ghs-pop-2020"
    }
  ]
}
```

**`results.json`**
```json
{
  "meta": {
    "engine_version": "0.1.0", "generated_at": "…", "seed": 20260918,
    "n_draws": 10000, "n_stored": 1000, "variant": "full",
    "dev_placeholders": false, "frozen_tag": "predictions-frozen-v1",
    "param_count": 42, "all_params_cited": true
  },
  "drugs": ["carbamazepine","atenolol","losartan","irbesartan","paracetamol","citalopram"],
  "results": [
    {
      "site_id": "TLS-03", "drug": "irbesartan",
      "pec_ng_l": { "p5": 12.1, "p50": 310.4, "p95": 5120.0 },
      "rq":       { "p5": 0.02, "p50": 0.61, "p95": 10.2 },
      "pnec_ng_l": 500.0, "lod_ng_l": 1.0,
      "score": 0.42, "tier": "medium", "lod_share": 0.97,
      "rank_in_city": 2, "n_in_city": 9,
      "drivers": [ { "param": "lambda", "rho": 0.71 }, { "param": "Q", "rho": -0.58 } ],
      "driver_sentence": "Mostly driven by assumed leakage (λ); flow (Q) second.",
      "flip": {
        "up":   { "param": "lambda", "multiplier": 1.4, "to_tier": "high" },
        "down": { "param": "lambda", "multiplier": 0.35, "to_tier": "low" }
      },
      "histogram": { "log10_edges": [ -3.0, -2.8, "…" ], "counts": [ 3, 7, "…" ] },
      "draws": { "offset": 57000, "count": 1000 },
      "provenance_keys": ["param:irbesartan:ddd_g", "param:irbesartan:fe", "prior:lambda", "cons:FR:irbesartan"],
      "fhir_ids": { "prediction": "Observation/pred-TLS-03-irbesartan" }
    }
  ],
  "site_overall": [ { "site_id": "TLS-03", "score": 0.42, "top_drug": "irbesartan", "rank_in_city": 2 } ],
  "city_summary": [ { "city": "TLS", "high": 3, "medium": 4, "low": 2 } ]
}
```
(PNEC and LOD values above are fixture placeholders, not real parameters.)

**`draws.bin`**: little-endian Float32, the stored RQ draws, concatenated in `results` order; each block is `n_stored` long and addressed by `draws.offset`. `draws_index.json` repeats offsets plus `dtype`, `endianness` and `n_stored`, for validation.

**Fixtures:** `contracts/fixtures/` holds a small realistic example (2 cities × 3 sites × 6 drugs) of every file, including `draws.bin`. These are generated by `scripts/make_fixtures.py` with a fixed seed and **obviously fake parameters**, with `meta.dev_placeholders=true`.

**Type generation:**
- Web: `pnpm run gen:types` → `web/src/types/contracts.ts` via `json-schema-to-typescript`.
- Python: pydantic models in `engine/src/pharmashed/contracts.py` hand-written to match. A test validates engine output against the JSON Schemas with `jsonschema`.

**Acceptance:** schemas lint; fixtures validate against schemas; TS types generate; a pytest validates fixtures.

---

## M02 — Parameter registry (drug parameters + priors)

**Path:** `data/params/`, `engine/src/pharmashed/params.py` · **Depends on:** M01.

**Purpose:** one cited table of every drug-specific number, plus a YAML of site-level priors; loaders that refuse uncited data.

**`drug_parameters.csv` columns**

| column | meaning |
|---|---|
| `drug` | lowercase INN |
| `param` | one of `atc`, `ddd_g`, `fe`, `R`, `k_per_h`, `pnec_ng_l`, `lod_ng_l` |
| `distribution` | `fixed`, `uniform`, `loguniform`, `triangular` |
| `value` | for `fixed` (or mode for triangular) |
| `min`, `max` | for ranged distributions |
| `unit` | |
| `source_title` | short citation |
| `source_url` | required unless `status=todo` |
| `source_note` | where in the source (table/page), and any conversion done |
| `evidence_quote` | verbatim text from the source containing the number (≤ 40 words) |
| `retrieved_at` | ISO date |
| `verified` | `none` · `agent` · `human` · `failed` |
| `verify_note` | verifier's reason when `failed` |
| `status` | `sourced` or `todo` |

The initial file ships with **all rows `status=todo` and empty values**, pre-populated with the 6 drugs × 7 params = 42 rows. Values are filled by researcher agents following `SOURCING.md` (S1 rules, S2 prompt), checked by a verifier session (S4), then reviewed by a human via `docs/sourcing_report.md`. Never filled from memory. `R` rows stay `todo` with note "not required: w=0 for all MVP sites"; the loader treats `R` as optional when every site has w=0.

**Freeze gate:** strict mode additionally requires every `sourced` row to have `verified ∈ {agent, human}`, and every `pnec_ng_l` row to have `verified=human`.

**`make sourcing-report`** (script `scripts/sourcing_report.py`) writes `docs/sourcing_report.md` as specified in SOURCING.md S6.

**`priors.yaml`** (site-level and structural priors):
```yaml
lambda:
  distribution: loguniform
  min: 0.002
  max: 0.15
  status: assumption
  sources: ["R22", "R23", "R24", "R19"]
  note: "Effective untreated fraction; bulk from city-wide exfiltration ~0.5–3% dwf, tail to 13% catchment-scale."
Q_by_size_class:          # m³/s, per hand-assigned channel size class
  S: { distribution: loguniform, min: 0.005, max: 0.1 }
  M: { distribution: loguniform, min: 0.02,  max: 0.5 }
  L: { distribution: loguniform, min: 0.1,   max: 2.0 }
  status: assumption
  note: "Team assumption scaled by visible channel width; capped at 2 m³/s for 1.5–8 m urban streams."
tau_h:
  distribution: uniform
  min: 0.5
  max: 12
  status: assumption
  note: "Travel time from input to site; team assumption; sensitivity shows its influence."
consumption_multiplier:
  distribution: uniform
  min: 0.8
  max: 1.25
  status: assumption
  note: "Spread for national→city transfer and year mismatch."
scenario_presets:
  sewer_repair:     { lambda: 0.5 }
  drought:          { Q: 0.2 }
  leakage_hotspot:  { lambda: 3.0 }
tiers: { high: 0.5, medium: 0.1 }
```
Every `status: assumption` entry is surfaced in the UI Methodology priors table with an "assumption" badge.

**`params.py` API**
```python
class ParamRow(BaseModel): ...              # mirrors CSV columns, validators enforce source rules
class DrugParams(BaseModel):                # one per drug, resolved distributions
    drug: str; atc: str
    ddd_g: Dist; fe: Dist; R: Dist; k_per_h: Dist; pnec_ng_l: Dist; lod_ng_l: Dist
def load_drug_params(path, mode: Literal["dev","strict"]) -> dict[str, DrugParams]
def load_priors(path) -> Priors
def provenance_entries() -> dict[str, ProvenanceEntry]   # keys like "param:irbesartan:fe"
```
`Dist` is a small dataclass `{kind, value, min, max}` with `.sample(rng, n)`.

**Rules enforced:**
- `status=sourced` ⇒ `source_url` and `source_note` non-empty, and values present and consistent with the distribution.
- `fe`, `R` ∈ [0,1]; `ddd_g`, `pnec_ng_l`, `lod_ng_l` > 0; `min < max`.
- Strict mode: any `todo` → `UnsourcedParameterError` listing every missing row.
- Dev mode: `todo` rows take values from `contracts/fixtures/dev_placeholders.yaml`, and the returned object flags `dev_placeholders=True`.

**CLI:** `pharmashed params check [--strict]` prints a table of sourced/todo per drug.

**Acceptance:** tests cover every validation rule; `make data-check` prints the status table; strict mode fails on the shipped file (expected until the human fills it).

---

## M03 — Consumption data

**Path:** `data/consumption/consumption.csv`, `engine/src/pharmashed/consumption.py` · **Depends on:** M02.

**Purpose:** DDD/1000 inhabitants/day per country × drug, with granularity recorded.

**Columns:** `country` (ISO2: PT, IT, FR, BE, NO), `drug`, `atc`, `year`, `ddd_per_1000_per_day`, `granularity` (`molecule` | `group_downscaled`), `group_value` (if downscaled), `molecule_share` (if downscaled), `share_source_url` (if downscaled), `source_title`, `source_url`, `source_note`, `status`.

Also carries `evidence_quote`, `retrieved_at`, `verified`, `verify_note` (same meaning as M02).

Ships as 30 `todo` rows (5 countries × 6 drugs). Filled by researcher agents per `SOURCING.md` S3 (one country per session), verified per S4, with the OECD group level as fallback.

**API**
```python
def load_consumption(path, mode) -> dict[tuple[str,str], ConsumptionRow]   # (country, drug)
def consumption_value(row) -> float     # molecule value, or group_value × molecule_share
```
**Rules:** downscaled rows require `molecule_share` ∈ (0,1] and `share_source_url`; never one share across countries (a test checks shares differ or are individually sourced).

**Acceptance:** loader tests; `make data-check` shows a country × drug matrix coloured by granularity.

---

## M04 — Sites and streams

**Path:** `data/sites/`, `engine/src/pharmashed/sites.py`, `scripts/fetch_streams.py`, `scripts/place_sites.md` · **Depends on:** M01.

**Purpose:** 8–10 hand-placed synthetic sites per city on real urban streams, plus stream geometry for the map.

**Automated rule-based placement: `scripts/auto_place_sites.py`** (full rules in `SOURCING.md` S5):
1. Overpass query for small waterways per city; candidate points every 150 m.
2. Stratify by GHS-POP density tertiles (needs M05's raster reader) and pick 3 per stratum, ≥ 800 m apart, seeded → 9 per city.
3. `size_class` from OSM `width` tag, else by waterway type.
4. All `synthetic: true`, `w: 0`, `valid: true`; write `sites.geojson` + `sites_preview.html`.
5. `--exclude TLS-04,GNT-07` re-runs after human preview rejects points.

Because placement uses population, run M05's raster reader before this script (M04 code can be written first; placement runs after M05).

**`fetch_streams.py`:** Overpass API query for `waterway~"stream|ditch|canal|river"` within each city bbox → `streams.geojson`, simplified (shapely `simplify(0.0001)`), with ODbL attribution in its properties.

**`sites.py` API**
```python
def load_sites(path) -> list[Site]
def cities() -> list[City]          # static: TLS/Toulouse/FR, GNT/Ghent/BE, BNV/Benevento/IT, CBR/Coimbra/PT, OSL/Oslo/NO
```
**Validation:** ids unique and prefixed by city; points inside city bbox; size_class ∈ {S,M,L}.

**Acceptance:** 40–50 sites load; `streams.geojson` < 3 MB total; a notebook/plot shows sites on streams.

---

## M05 — Population near each site

**Path:** `engine/src/pharmashed/population.py`, `scripts/fetch_ghspop.py` · **Depends on:** M04.

**Purpose:** `P[s]` = population within a buffer (default 500 m) from the GHS-POP 100 m grid.

**Steps:**
1. `fetch_ghspop.py` downloads the GHS-POP tiles covering the five cities into `data/raw/` (verify the current release and tile naming on the JRC GHSL site; record the release in `provenance`).
2. `population.py`:
   ```python
   def population_in_buffer(site: Site, raster_paths, radius_m=500) -> float
   ```
   Reproject the site point to the raster CRS (GHS-POP uses Mollweide, ESRI:54009), buffer in metres, `rasterio.mask` with `all_touched=False`, sum cell values. Cache results into `sites.json` (`population_buffer`).
3. `pharmashed population compute` writes populations back into the build copy of `sites.json`.

**Pitfalls:** buffer in a metric CRS, not degrees; nodata handling; tiles spanning boundaries (merge with `rasterio.merge` first).

**Acceptance:** a unit test with a synthetic 3×3 raster gives the exact expected sum; all sites get a population > 0 (flag any zero for review).

---

## M06 — Priors and sampling

**Path:** `engine/src/pharmashed/priors.py` · **Depends on:** M02.

**Purpose:** turn parameters and priors into draw arrays of shape `(N_DRAWS,)`.

**API**
```python
def sample_dist(dist: Dist, rng, n) -> np.ndarray
def sample_site_inputs(site, priors, rng, n) -> dict[str, np.ndarray]   # lambda, Q, tau
def sample_drug_inputs(drug_params, rng, n) -> dict[str, np.ndarray]    # ddd, fe, R, k, pnec, lod
def sample_consumption(value, priors, rng, n) -> np.ndarray             # value × multiplier
```
**Details:**
- `loguniform(min,max)`: `exp(uniform(log min, log max))`.
- `triangular`: `rng.triangular(min, mode, max)`.
- `fixed`: `np.full(n, value)`.
- Q uses `priors.Q_by_size_class[site.size_class]`.
- One RNG per (site, drug) derived with `np.random.SeedSequence(seed).spawn(...)` in a deterministic order, so results do not depend on iteration order.

**Acceptance:** tests check bounds, the log-uniform median ≈ geometric mean, determinism under a fixed seed, and independence of order.

---

## M07 — Model core

**Path:** `engine/src/pharmashed/model.py` · **Depends on:** M06.

**Purpose:** vectorised implementation of A4, pure functions, no I/O.

**API**
```python
Variant = Literal["full", "wwtp_only", "pop_only"]
def pec_ng_l(P, C, ddd_g, fe, lam, w, R, Q_m3s, k_per_h, tau_h) -> np.ndarray
def rq(pec, pnec) -> np.ndarray
def apply_variant(inputs: dict, variant: Variant, cross_country_mean_C: float) -> dict
```
- `wwtp_only`: `lam = 0`.
- `pop_only`: `C` replaced by the cross-country mean for that drug.
- All arrays broadcast; no Python loops over draws.

**Tests (hand-computed):**
- Single draw with round numbers reproduces a hand calculation to 1e-9.
- w=0 and λ=0 ⇒ PEC = 0.
- Doubling Q halves PEC; doubling λ doubles PEC when w=0.
- `RQ·mλ·mC/mQ` equals recomputing with scaled inputs (this guards the client-side shortcut in M20).

**Acceptance:** all tests pass; functions have docstrings with units.

---

## M08 — Monte Carlo runner

**Path:** `engine/src/pharmashed/montecarlo.py`, `cli.py` · **Depends on:** M03, M05, M07.

**Purpose:** for every site × drug: sample, compute PEC and RQ, keep summaries plus stored draws.

**API**
```python
@dataclass
class PairResult:
    site_id: str; drug: str
    pec: np.ndarray; rq: np.ndarray; inputs: dict[str, np.ndarray]   # full N_DRAWS, in memory only
def run_pair(site, drug, ctx, variant="full") -> PairResult
def run_all(ctx, variant="full") -> list[PairResult]
```
`ctx` bundles params, priors, consumption, seed and mode.

**Performance:** 50 sites × 6 drugs × 10,000 draws = 3M evaluations, well under a second vectorised. Run pairs in a simple loop; no multiprocessing needed.

**CLI:** `pharmashed run [--strict] [--variant full] [--out data/build]` → calls M09–M11.

**Acceptance:** `make run` completes in < 30 s in dev mode; output validates against schemas.

---

## M09 — Sensitivity, drivers and flip thresholds

**Path:** `engine/src/pharmashed/sensitivity.py` · **Depends on:** M08.

**Purpose:** per pair, which inputs drive RQ, plus the multipliers that change the tier.

**Drivers:** Spearman rank correlation between each sampled input (`lambda`, `Q`, `C`, `fe`, `k`, `tau`, `ddd`, `pnec`) and `rq`, via `scipy.stats.spearmanr`. Drop inputs that are `fixed` (zero variance). Sort by |ρ|, keep the top 5.

**Driver sentence:** a template from the top two drivers using the glossary names:
`"Mostly driven by {name1} ({sym1}); {name2} ({sym2}) second."` Names come from a shared `glossary.json` (also used by the web).

**Flip thresholds (closed form, w=0):** the score after multiplying RQ by `m` is `P(RQ·m > 1) = P(RQ > 1/m)`. To reach score `b`, `m_b = 1 / quantile(RQ, 1 − b)`.
- For current tier high → the `down` flip targets b = 0.5; medium → `up` b = 0.5 and `down` b = 0.1; low → `up` b = 0.1.
- Express as a multiplier on λ (or on 1/Q, reported as a Q multiplier `1/m`), picking the top driver among {λ, Q}.
- Cap reported multipliers to [0.01, 100]; beyond that report "not reachable within plausible range".

**Acceptance:** tests on synthetic arrays where the answer is known (e.g. `rq = lognormal` with known quantiles); the driver sign for Q is negative.

---

## M10 — Scoring, tiers and ranking

**Path:** `engine/src/pharmashed/scoring.py` · **Depends on:** M08.

**API**
```python
def score(rq) -> float                    # mean(rq > 1)
def lod_share(pec, lod) -> float
def tier(score, tiers_cfg) -> Literal["high","medium","low"]
def rank_in_city(results) -> None         # per (city, drug): rank by score desc, tie-break by rq.p50 desc
def site_overall(results) -> list          # per site: max score over drugs, top_drug, rank in city
def city_summary(results) -> list          # counts of tiers using site_overall
def histogram(rq, bins=40) -> dict         # log10 edges over [p0.1, p99.9], counts
```
**Acceptance:** unit tests for ties, tier boundaries (exactly 0.5 → high), and histogram counts summing to N_DRAWS.

---

## M11 — Exporters and freeze

**Path:** `engine/src/pharmashed/export.py`, `freeze.py` · **Depends on:** M09, M10.

**Outputs (to `--out`, default `data/build/`):**
- `sites.json`, `results.json`, `draws.bin`, `draws_index.json`
- `provenance.json`: every key referenced by `provenance_keys` → `{label, value, unit, distribution, source_title, source_url, source_note, status}`
- `methodology.json`: model stages (for the diagram), the priors table (from `priors.yaml` and the params CSV), the identifiability text (copied from docs §5.5), and **ablation rankings** (run variants `full`, `pop_only`, `wwtp_only`, and store per-city site rankings by `site_overall.score` for each)
- `glossary.json`: symbol, plain name and one-line definition for PEC, PNEC, RQ, LOD, λ, Q, τ, k, fe, DDD, score

**Freeze (`make freeze`):**
1. Refuse if the git working tree is dirty or mode is dev.
2. Run strict → write to `data/frozen/`.
3. Write `data/frozen/FROZEN.json`: `{sha256 of results.json, engine_version, git_commit_before, created_at}`.
4. `git add data/frozen && git commit -m "freeze predictions v1" && git tag predictions-frozen-v1`.
5. Set `results.meta.frozen_tag` in the frozen copy (write before hashing).

**Acceptance:** all outputs validate against schemas; freeze produces a tag; re-running freeze without changes is refused (tag exists).

---

## M12 — Consistency checks

**Path:** `engine/src/pharmashed/checks/` · **Depends on:** M11 (frozen outputs), `data/observed/`.

**Import rule:** this is the **only** package allowed to read `data/observed/`. `tests/test_separation.py` greps `engine/src/pharmashed/` (excluding `checks/`) for `observed` and `rodrigues` and fails on any hit. It also checks that `checks/` never writes to `data/frozen/`.

**Pre-check:** verify `sha256(data/frozen/results.json)` equals `FROZEN.json`, and that the tag exists. If not, abort with "checks must run on frozen predictions".

**Checks (definitions are pre-registered and fixed here):**

| ID | Computation | Output |
|---|---|---|
| C1 | For drugs with public observed detection frequency (irbesartan 73%, carbamazepine 58%, paracetamol 31%): predicted = mean over all sites of `lod_share`. Report the Spearman ρ between predicted and observed (n=3) and the paired values. Requires `lod_ng_l` sourced; else status `unavailable` | scatter data, ρ, n |
| C2 | Per city: predicted = mean over sites of Σ_drugs PEC p50. Compare the city order with Toulouse > Ghent > Benevento > Coimbra > Oslo. Kendall τ. Note: observed totals cover 16 drugs, predicted cover 6 | both orders, τ |
| C3 | Oslo's predicted C2 rank ≠ 1 | pass/fail; flagged "designed with knowledge of answer" |
| C4 | For each (city, drug) with a public observed city maximum (irbesartan TLS/BNV/CBR; paracetamol GNT/OSL): predicted = max over the city's sites of `pec.p95`. Pass ⇔ observed ≤ predicted **and** predicted/observed ≤ 10 | rows with observed, predicted, ratio, pass |
| C5 | From `methodology.json` ablations: per city, the ranking under each variant; report how many site-rank changes each step causes, and that `wwtp_only` gives PEC = 0 everywhere | table |

Observed values are read from `observed_rodrigues2025.csv` by `(compound, metric, scope)` lookup (e.g. `irbesartan, max_concentration, Toulouse`). Note `acetaminophen` in the CSV = `paracetamol` in the engine (mapping table in `checks/observed.py`).

**Output:** `data/build/checks.json` per `checks.schema.json`, including `circularity_statement` (text from docs §7.1) and `frozen_tag`, `frozen_sha256`.

**Acceptance:** separation test passes; checks run against fixture-frozen data in tests; each check reports `pass | fail | unavailable` with a reason.

---

## M13 — FHIR terminology

**Path:** `fhir/terminology/` · **Depends on:** —.

**Purpose:** publish our custom codes properly so the validator resolves them.

**Resources:**
1. `CodeSystem-pharmashed-observation-category.json`
   - `url`: `https://pharmashed.example/fhir/CodeSystem/observation-category` (replace the domain with the repo's GitHub Pages URL if published)
   - concept `model-prediction` ("Model prediction — computed output of the PharmaShed screening model, not a measurement")
2. `CodeSystem-pharmashed-components.json`: `pec-p05`, `pec-p50`, `pec-p95`, `rq-p50`, `priority-score`, `lod-share`, `validity`
3. `CodeSystem-pharmashed-consumption.json`: `ddd-per-1000-per-day`, `granularity-molecule`, `granularity-group-downscaled`
4. `ValueSet-pharmashed-observation-category.json`: includes `model-prediction` plus the core `laboratory` code from `http://terminology.hl7.org/CodeSystem/observation-category`

Use `status: draft`, `experimental: true`, `content: complete`.

**Acceptance:** each resource validates standalone with the validator (M15).

---

## M14 — FHIR builder

**Path:** `engine/src/pharmashed/fhir/` · **Depends on:** M11, M13.

**Purpose:** turn `sites.json`, `consumption.csv`, `results.json` and provenance into FHIR resources and bundles.

**Resources:**

| Resource | Id pattern | Key content |
|---|---|---|
| `Location` | `site-{site_id}` | name, position (lat/lon), `meta.tag` synthetic, description noting synthetic placement. Apply the OneAquaHealth IG Location profile if the IG defines one (check the IG artifacts page; record the finding in CONTEXT decisions) |
| `Group` | `pop-{country}` | type `person`, actual false, characteristic = country (ISO 3166 code) |
| `Observation` (consumption) | `cons-{country}-{drug}` | subject Group; code = ATC (`http://www.whocc.no/atc`); valueQuantity DDD/1000/day; component `granularity-*`; category `survey` |
| `Observation` (prediction) | `pred-{site_id}-{drug}` | `meta.profile` = `http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-with-component-oah`; category = `model-prediction` (our CodeSystem); code = ATC drug; subject Location; `method.text` "PharmaShed PEC {engine_version}, variant full"; components per M13 (pec-p05/p50/p95 in ng/L UCUM `ng/L`, rq-p50, priority-score, lod-share); `derivedFrom` → consumption Observation; `meta.tag` `model-output` |
| `Observation` (reference measurement) | `ref-{city}-{drug}-{metric}` | category `laboratory`; subject Location for the city (or a city-level Location); valueQuantity; `meta.tag` `external-reference-R1` |
| `Provenance` | `prov-{site_id}-{drug}` | target the prediction; agent = PharmaShed (Device); entity.what → consumption Observation plus `display` entries for each parameter source (title + URL) |

**Bundles** (type `collection`): `terminology.json`, `locations.json`, `consumption.json`, `predictions-{city}.json`, `reference-measurements.json`. Also write `fhir_index.json` (resource counts per type, bundle list).

**API**
```python
def build_all(build_dir, out_dir) -> FhirIndex
```
**Acceptance:** bundles parse with `fhir.resources`; ids are deterministic; one hand-checked prediction Observation matches the IG example structure.

---

## M15 — FHIR validation and HAPI server

**Path:** `fhir/validator/validate.sh`, `infra/docker-compose.yml`, `scripts/load_hapi.py` · **Depends on:** M13, M14.

**Validator:**
- `validate.sh` downloads `validator_cli.jar` (latest release from the HL7 FHIR core GitHub releases) if absent.
- Runs: `java -jar validator_cli.jar fhir/out/*.json -version 4.0.1 -ig fhir/terminology -ig <OneAquaHealth IG package or URL> -output fhir/out/validation.json`.
- **Verify** how to load the OneAquaHealth CI-build IG. Options: the package from `build.fhir.org/ig/hl7-eu/oah/package.tgz`, or a local copy. Record the working command in CONTEXT decisions.
- Parse the OperationOutcome; summarise error/warning counts into `fhir_index.json.validation = {status, errors, warnings, validator_version, ran_at}`.
- Errors fail CI; warnings are listed.

**HAPI (local demo only):**
- `docker-compose.yml`: service `hapi` (image `hapiproject/hapi:latest`, port 8080, env enabling R4). Optionally the `api` service.
- `load_hapi.py`: POST each bundle as a `transaction` (convert collection → transaction with PUT by id).
- Query demo: run `Observation?category=laboratory` and `Observation?category=https://…|model-prediction`, then write the counts into `fhir_index.json.query_demo`. In the hosted demo these counts come from the file; locally they can be refreshed live.

**Acceptance:** `make fhir-validate` → 0 errors; `make hapi-up` loads all bundles; the two queries return non-overlapping, non-zero counts.

---

## M16 — API (FastAPI)

**Path:** `api/src/pharmashed_api/` · **Depends on:** M11, M12, M14.

**Purpose:** serve build artefacts, the server-side scenario endpoint and the assistant. Static-first, so the web app can also work from files alone.

**Endpoints:**

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | ok + engine version |
| GET | `/api/meta` | `results.meta` |
| GET | `/api/sites` | `sites.json` |
| GET | `/api/results` | `results.json` |
| GET | `/api/draws.bin` | binary (`application/octet-stream`) |
| GET | `/api/checks` | `checks.json` |
| GET | `/api/methodology` | `methodology.json` |
| GET | `/api/provenance/{key}` | one provenance entry |
| GET | `/api/glossary` | `glossary.json` |
| GET | `/api/fhir/index` | `fhir_index.json` |
| GET | `/api/fhir/bundle/{name}` | a bundle |
| POST | `/api/scenario` | body `{site_id, drug, multipliers:{lambda,Q,C}}` → `{score, tier, rq_quantiles}` computed from stored draws (same math as the client) |
| POST | `/api/assistant` | see M17 |

- Data directory from env `PHARMASHED_DATA` (default `data/build`, or `data/frozen` for the demo).
- CORS for the web dev origin.
- Load JSON once at startup; cache the draws as a numpy memmap.

**Acceptance:** pytest with `TestClient` on fixture data; `/api/scenario` matches `model.py` rescaling to 1e-6.

---

## M17 — Assistant

**Path:** `api/src/pharmashed_api/assistant/` · **Depends on:** M16.

**Purpose:** answer questions using tools only; never compute science itself.

**Tools** (JSON schemas passed to the Messages API):

| Tool | Args | Implementation |
|---|---|---|
| `list_priority_sites` | `city`, `drug?`, `limit=5` | filter `results.json` / `site_overall` |
| `get_site_profile` | `site_id` | all drugs for a site: quantiles, score, tier, rank, validity |
| `explain_drivers` | `site_id`, `drug` | drivers, sentence, flip |
| `run_scenario` | `site_id`, `drug`, `multipliers` | same function as `/api/scenario` |
| `get_provenance` | `key` | provenance entry |

**Loop:** standard tool-use loop (max 6 tool rounds). System prompt:
- Role: explain PharmaShed outputs to officers and researchers.
- Every number must come from a tool result in this turn.
- Always state that scores reflect assumed priors ("under stated assumptions").
- Never claim a stream is safe or unsafe. For swimming or drinking questions, say what the model does not estimate and point to official water-quality sources.
- Plain language first, symbols second, using the glossary names.

**Numeric guard (`guard.py`):**
- Extract numbers from the final answer (regex for ints, decimals, percentages, scientific notation).
- Collect all numbers from the tool results in the turn (flattened JSON), plus derived forms (value ×100 for percentages, rounded to 0–3 decimals).
- Allow small integers that appear in the question or in ids (e.g. ranks, "2 of 9").
- Any unmatched number → one retry with a correction message; if still failing, return the answer with `guard: {status: "warn", unmatched: [...]}`, which the UI shows as a warning chip.

**Response shape:** `{answer_markdown, tool_calls: [{name, args}], links: [{label, target_tab, site_id?, drug?}], guard}`.

**Model:** `ASSISTANT_MODEL` env (default `claude-sonnet-5`); temperature 0.2; max_tokens ~800.

**Eval (`eval/questions.yaml`, 12–15 items):** each has a question, expected tool names (subset match), must-contain strings, and must-not-contain patterns (e.g. "safe to swim"). `make eval-assistant` runs them and writes `eval/report.json` (pass rate, per-item detail) for the README.

**Acceptance:** eval ≥ 80% pass; the guard has unit tests with crafted answers.

---

## M18 — Web shell and data layer

**Path:** `web/src/` · **Depends on:** M01 (fixtures only — no engine needed).

**Structure:**
```
web/src/
├── main.tsx, App.tsx
├── types/contracts.ts          # generated (M01)
├── data/
│   ├── loaders.ts              # fetch JSON + draws.bin (from /api or /data static)
│   ├── draws.ts                # Float32Array view + slice(site, drug)
│   └── store.ts                # Zustand: city, site, drug, tab, scenario multipliers, drawers
├── components/
│   ├── shell/ TopTabs, FooterStrip, DevBanner, StateViews (Loading/Empty/Invalid)
│   ├── glossary/ Term (inline term with definition popover)
│   ├── provenance/ InfoButton, ProvenanceDrawer
│   └── charts/ BandChart, DrawHistogram, Tornado, DotOnBand, Scatter, ModelDiagram
├── tabs/ Explore/, Scenarios/, Consistency/, Methodology/, Fhir/
└── assistant/ AssistantDrawer
```
- Data source switch: `VITE_DATA_BASE` = `/api` (dev with API) or `/data` (static files copied by `make demo-build`). The app must work fully static except for the assistant.
- **FooterStrip** (always visible): `N = {n_draws} draws · engine {version} · predictions frozen {frozen_tag or "not frozen"} · {param_count} parameters, {all cited | X uncited}`.
- **DevBanner:** red, shown when `meta.dev_placeholders` is true.
- **StateViews:** every panel uses loading, empty (with reason) and invalid states; never render a blank div.
- **Glossary `Term` component:** every PEC / PNEC / RQ / λ / Q / score mention uses it, so the wording is identical everywhere.
- Layout: left map rail (~45%), right inspector (~55%), top tabs `Explore · Scenarios · Consistency · Methodology · FHIR`, assistant button top-right opening a slide-over. Desktop only (min width 1200 px).

**Acceptance:** app renders every tab with fixtures; types compile strictly; switching `VITE_DATA_BASE` works.

---

## M19 — Explore tab (map + site inspector)

**Path:** `web/src/tabs/Explore/`, `components/charts/` · **Depends on:** M18.

**Map rail (`MapView.tsx`):**
- MapLibre with a free raster basemap (e.g. Carto Positron; check attribution terms). Streams layer from `streams.geojson` as thin blue lines.
- Sites as circles: fill = sequential colour-blind-safe scale on `score` for the selected drug (or overall); **shape/size by tier** (e.g. radius 6/9/12 plus a ring for high), so colour never carries meaning alone.
- Controls above the map: city switcher (fly-to), drug switcher (All + 6 drugs), per-city summary chips "3 high · 4 medium · 2 low".
- Hover tooltip: name, "#rank of n", score, first four words of the driver sentence.
- Click → select site (store).

**Inspector (`SiteInspector.tsx`), top to bottom:**
1. Header: site name, `Synthetic site` badge, rank badge "#2 of 9 in Toulouse", validity flag.
2. `BandChart`: one row per drug, log10 x-axis in ng/L; p5–p95 bar, emphasised p50 tick, PNEC as a labelled dashed line, LOD as a lighter dashed line; rows sorted by `rq.p50` desc; bar fill by score. Permanent microcopy under the chart: "Ranges under stated assumptions — see Methodology." An `InfoButton` next to each PNEC and LOD label.
3. Row click → expansion:
   - `DrawHistogram` from `results.histogram` (log10 RQ), with a vertical line at RQ = 1, the exceedance area shaded, and the label "score = 0.42 (share of 10,000 draws with RQ > 1)".
   - `Tornado` from `drivers` (signed bars), plus `driver_sentence`.
   - Flip line: "Drops to Low if leakage × 0.35 · Rises to High if leakage × 1.4" from `flip`.
4. `ProvenanceDrawer`: right-side overlay listing value, unit, distribution, source title, URL and note, fetched by key. An ⓘ appears next to every number shown.

**Chart implementation notes:** plain SVG with a small `scaleLog` helper (d3-scale is fine to import alone); fixed row height 28 px; accessible `<title>` elements; keyboard focus on rows.

**Acceptance:** with fixtures, selecting sites and drugs updates the map and inspector; all ⓘ open the correct entries; a vitest checks the log-scale helper and sort order.

---

## M20 — Scenarios tab (client-side recompute)

**Path:** `web/src/tabs/Scenarios/`, `web/src/data/scenario.ts` · **Depends on:** M18, M19 charts.

**Math (`scenario.ts`) — must mirror A4 and M16:**
```ts
// stored = Float32Array of N_STORED RQ draws for (site, drug); valid only when site.w === 0
export function applyScenario(stored, m: {lambda: number; Q: number; C: number}) {
  const f = m.lambda * m.C / m.Q;
  let exceed = 0;
  const scaled = new Float32Array(stored.length);
  for (let i = 0; i < stored.length; i++) { const v = stored[i] * f; scaled[i] = v; if (v > 1) exceed++; }
  return { score: exceed / stored.length, quantiles: quantiles(scaled, [0.05, 0.5, 0.95]) };
}
```
PEC bands are rescaled by the same factor `f`. The baseline score comes from `results.score`, so scenario scores (computed on 1,000 draws) are shown with the note "recomputed live over 1,000 stored simulation draws". The baseline is recomputed on the same 1,000 draws too, so the delta compares like with like.

**UI:**
- Site and drug selection shared with Explore.
- **Preset cards first:** Sewer repair (λ×0.5), Drought (Q×0.2), Leakage hotspot (λ×3 — "Barcelona-type high-leakage case"), each with one line naming the real-world action it represents. Plus **Riparian restoration (illustrative)**: a card with its own slider "assumed extra in-stream removal 0–50%", default 0, badged "Illustrative — not part of the core model"; it multiplies RQ by (1 − removal).
- Fine sliders below: λ multiplier (0.1–10, log), Q multiplier (0.1–10, log), consumption multiplier (0.5–2).
- **Before/after:** BandChart with the baseline ghosted behind the scenario; tier chips before → after; delta readout "score 0.62 → 0.31".
- Footnote: "The model constrains λ/Q jointly — these controls show how much each assumption carries."
- If `site.w !== 0` → call `/api/scenario` instead (not expected in MVP).

**Acceptance:** vitest compares `applyScenario` against fixture expectations computed in Python (a shared fixture `scenario_cases.json` generated by M01's script); sliders update in < 16 ms for one pair.

---

## M21 — Consistency and Methodology tabs

**Path:** `web/src/tabs/Consistency/`, `web/src/tabs/Methodology/` · **Depends on:** M18, M19 charts; data from M11/M12.

**Consistency (`checks.json`):**
- Top: a distinct callout with `circularity_statement`.
- One card per check (C1–C5), status chip pass/fail/unavailable; failures in red with the §7.4 interpretation text; "unavailable" shows the reason (e.g. "LOD not yet sourced").
- C4: `DotOnBand` — observed max as a dot over the predicted `[min p5, max p95]` band on a log axis, ratio printed, pass chip.
- C1: small `Scatter` of predicted LOD share vs observed detection frequency, labelled points, ρ and n printed.
- C2/C3: two ordered lists side by side (observed vs predicted city order), τ printed.
- C5: small table of rank changes per ablation step.
- Footer: "Predictions committed before comparison — tag `{frozen_tag}`, sha256 `{short}`", linking to the GitHub tag.

**Methodology (`methodology.json`):**
- `ModelDiagram`: horizontal stages Consumption → Excretion → Pathways (untreated λ / treated w·(1−λ)·(1−R)) → Dilution (Q) → In-stream loss (k, τ) → RQ (PNEC). Each stage shows its symbol, prior summary and an ⓘ.
- Priors table: parameter, distribution, range, unit, status badge (sourced / assumption), a tiny SVG shape thumbnail, source link.
- Identifiability box: highlighted text from §5.5.
- **Ablation toggle:** segmented control `Population only · + Consumption · + Untreated pathway (full)`, plus a separate chip "WWTP-only (ePiE-like): predicts 0 for these streams". Shows per-city site ranking lists that reorder when toggled.

**Acceptance:** renders with fixtures, including "unavailable" states; the ablation toggle reorders lists.

---

## M22 — FHIR tab and Assistant drawer

**Path:** `web/src/tabs/Fhir/`, `web/src/assistant/` · **Depends on:** M18; data from M14/M15; API from M17.

**FHIR tab:**
- Left: resource types with counts (`fhir_index.json`); terminology resources listed as first-class items.
- Right: a collapsible JSON tree (small custom component) of the selected resource, highlighting `category`, `method`, `derivedFrom`, `component[priority-score]` and `meta.tag`.
- **Lab vs model panel:** the two queries from `query_demo`, shown as code, with their counts side by side, plus the sentence "A server query can distinguish model output from lab results via category `model-prediction`."
- Validation badge: green "Validates against OneAquaHealth IG" (errors = 0) or amber with counts; links to the CI log URL stored in `fhir_index.json`.
- Download buttons per bundle.

**Assistant drawer:**
- Slide-over from any tab; input box; suggested-question chips from the eval set.
- Each answer shows **tool-call chips** above it (`explain_drivers → get_provenance`).
- Links in answers (`links[]`) navigate to the tab and site/drug.
- A guard warning chip if `guard.status == "warn"`.
- Standing footer: "Scores reflect assumed priors; this assistant never computes values itself."
- Disabled state with explanation when the API is unavailable (static demo without a key).

**Acceptance:** works against the local API; degrades cleanly in static mode.

---

## M23 — CI

**Path:** `.github/workflows/ci.yml` · **Depends on:** everything, incrementally.

**Jobs:**
1. `python`: uv sync → ruff → pytest (engine + api), including schema validation of fixtures and the separation test.
2. `data`: `pharmashed params check` (dev) — prints status; a job annotation lists todo rows. The strict check runs only on the `predictions-frozen-*` tag.
3. `fhir`: set up Java 17 → build bundles from fixtures (or frozen data if present) → `validate.sh` → upload `validation.json` as an artifact → fail on errors.
4. `web`: pnpm install → gen types → typecheck → vitest → build.

**Acceptance:** green on main; the README shows the badge.

---

## M24 — Docs, README and demo script

**Path:** `README.md`, `docs/demo-script.md`, `docs/sources.md` · **Depends on:** all.

**README sections:** one-line pitch; screenshot; what it is / is not (from docs §4); quickstart (`make setup && make run && make web`); architecture diagram; the consistency-check summary (auto-pasted from `checks.json`); assistant eval pass rate; data licences (OSM ODbL, GHS-POP, national consumption sources); the list of assumptions; links to docs.

**Demo script (3–5 min) — every step maps to a module:**
1. Problem in one sentence + "existing models predict zero here" (Methodology ablation chip, M21).
2. Explore Toulouse, click the top site (M19).
3. Irbesartan band crossing PNEC → expand → draw histogram → tornado "driven by leakage" (M19).
4. Scenarios → Sewer repair preset → tier drops, delta readout (M20).
5. Consistency → circularity callout → one pass, one honest miss (M21).
6. Methodology → ablation toggle reorders ranking (M21).
7. FHIR → lab vs model query counts → validator badge (M22).
8. Assistant → "Why is TLS-03 high priority?" → tool chips (M22).
9. Close: what the consortium would need to turn screening into validation.

**Acceptance:** a fresh clone following the README quickstart reaches a working app.

---

## Part C — Build order and dependency graph

```
M00 → M01 ──┬─────────────────────────────► M18 → M19 → M20 → M21 → M22
            │                                  (web builds on fixtures)
            ├─ M02 → M03 ─┐
            ├─ M04 → M05 ─┼─ M06 → M07 → M08 → M09 → M10 → M11 → M12
            │             │                                 │
            └─ M13 ───────┴──────────────────────────────── M14 → M15
                                                            │
                                         M16 → M17 ◄────────┘
M23 grows with each module; M24 last.
```

**Phases** (each phase ends with a CHECKPOINT update):
1. **Foundations:** M00, M01
2. **Data layer:** M02, M03, M04, M05 (the code; human data sourcing runs in parallel)
3. **Engine:** M06 → M11
4. **Web on fixtures:** M18 → M22 (can start right after Phase 1)
5. **Checks + FHIR:** M12, M13, M14, M15
6. **API + assistant:** M16, M17
7. **Integration:** swap fixtures for real build outputs; M23, M24; freeze; run checks; record the demo

**Critical path to the freeze:** human sourcing of `drug_parameters.csv` + `consumption.csv` → strict run → freeze. Nothing else blocks the freeze, so start the sourcing immediately.

---

## Part D — Risk register (implementation)

| Risk | Mitigation |
|---|---|
| Parameters can't all be sourced | Dev mode keeps building; the Methodology table shows "todo" honestly; the freeze waits. Drop a drug rather than invent a value |
| Molecule-level consumption unavailable for a country | Group-downscaled with a country-specific share and a per-country provenance flag |
| OneAquaHealth IG won't load in the validator | Validate against base R4 + our terminology; record the attempt in CONTEXT; keep the profile URL in `meta.profile` |
| GHS-POP download size or format issues | Clip to city windows once; cache populations in `sites.json`; the fixture populations keep the web unblocked |
| Flip thresholds odd for extreme tails | Cap multipliers; show "not reachable within plausible range" |
| Assistant hallucinates numbers | Numeric guard + eval; tool-call chips make behaviour visible |
| Client/server scenario math drift | Shared `scenario_cases.json` fixture tested in both vitest and pytest |
