# CHECKPOINT.md — progress log (read second, update last)

## How to use this file (session protocol)

**Start of every session (costs very few tokens):**
1. Read `CONTEXT.md` and this file. Nothing else yet.
2. Pick exactly **one** module from "Next up".
3. Load only that module: `sed -n '/^## M07/,/^## M08/p' IMPLEMENTATION.md`. Also load Part A4 (equations) if the module touches the model.
4. Read only the files that module touches. Don't open the whole repo.

**During the session:**
- Work to the module's acceptance list. Run the tests.
- If something outside the module needs changing, add it to "Follow-ups". Don't do it now.
- If a decision is made, append it to CONTEXT.md §4 with the next D-number.

**End of every session (mandatory, even if unfinished):**
1. Update the module status table (status + short note).
2. Replace "Last session" with 3–6 lines: what changed, which tests pass, anything half-done (file + function).
3. Set "Next up" to the next 1–3 modules.
4. Commit: `git commit -m "Mxx: <summary> [checkpoint]"`.

**Session starter prompt (paste into a fresh session):**
```
Read CONTEXT.md and CHECKPOINT.md only. Then work on module <Mxx>:
load it with `sed -n '/^## Mxx/,/^## Myy/p' IMPLEMENTATION.md`.
Follow the hard rules in CONTEXT §5. Stop when the acceptance list passes,
then update CHECKPOINT.md per its protocol. Keep responses terse; show diffs, not whole files.
```

**Token-saving rules:**
- One module per session; start a new session instead of continuing a long one.
- Ask for diffs or edits, not full file rewrites.
- Never paste large data files into the chat; refer to them by path.
- Run tests locally and paste only failing output.
- Web modules build against `contracts/fixtures/`, so they never need the engine running.

---

## Status

Legend: ☐ not started · ◐ in progress · ☑ done (acceptance passed) · ⛔ blocked

| ID | Module | Status | Note |
|---|---|---|---|
| M00 | Repo scaffold | ☑ | uv workspace + Vite web app + Makefile; `make setup && make test` passes |
| M01 | Contracts + fixtures + types | ☑ | 7 schemas, fixtures (2 cities x 3 sites x 6 drugs), pydantic + TS types generated |
| M02 | Parameter registry | ☑ | Loader + CLI done; values = agent tasks A1–A6 (blocked on those) |
| M03 | Consumption data | ☑ | Loader + CLI done; values = agent tasks A7–A11 |
| M04 | Sites + streams | ☑ | Now 105 sites (21/city, auto-placed from OSM streams, D41); loader + CLI; fetch_streams.py + auto_place_sites.py |
| M05 | Population (GHS-POP) | ☑ | 4 tiles downloaded; real 500 m populations in `sites.geojson` (2 Oslo sites are zero, flagged) |
| M06 | Priors + sampling | ☑ | priors.py (unit-tested; not yet run end to end on the 105 sites) |
| M07 | Model core | ☑ | model.py |
| M08 | Monte Carlo runner | ☑ | `pharmashed run`: 105 sites x 6 drugs x 1,000 draws in about 1.5 s; N_DRAWS = 1,000 (D40) |
| M09 | Sensitivity + flips | ☑ | sensitivity.py |
| M10 | Scoring + ranking | ☑ | scoring.py |
| M11 | Exporters + freeze | ☑ | export_build writes all 7 artifacts; freeze.py locks + tags; 12 tests |
| M12 | Consistency checks | ☑ | C1-C5 run on the frozen illustrative run: C1, C2, C5 pass; C3, C4 fail (illustrative inputs, not evidence, D35); separation test |
| M13 | FHIR terminology | ☑ | 4 terminology JSON files (3 CodeSystems + 1 ValueSet) |
| M14 | FHIR builder | ☑ | builder.py: Location/Group/Consumption/Prediction bundles; 18 tests |
| M15 | Validator + HAPI | ☑ | HL7 validator run on all 10 bundles against the OAH IG (pinned commit): 0 errors, 1,513 warnings, recorded in `fhir_index.validation`. The local HAPI server (docker compose) has not been run |
| M16 | API | ☑ | FastAPI app; core/scenario/fhir routes; 15 tests |
| M17 | Assistant | ☑ | api/assistant/: tool-use loop, numeric guard, usage limits (S3). Provider is OpenAI `gpt-5-mini` with Groq fallback, not Anthropic (D25: model from env). Needs `OPENAI_API_KEY` |
| M18 | Web shell + data layer | ☑ | Vite + React + Zustand; Vercel deploy; light/dark theme |
| M19 | Explore tab | ☑ | Map (glow layers, S6), site inspector, top-sites empty state (S7) |
| M20 | Scenarios tab | ☑ | Client-side scenarios (D13) + "why does it change" explanations |
| M21 | Consistency + Methodology tabs | ☑ | |
| M22 | FHIR tab + Assistant drawer | ☑ | Drawer opens with site context; FHIR badge honest about validation |
| M23 | CI | ☐ | `.github/workflows/` is empty. Note: PR #14 reused the label "M23" for site-density work, which is not this |
| M24 | Docs + demo script | ◐ | README rewritten. `docs/` is empty (`docs/PharmaShed.md` still missing, see Blockers). Demo script lives in local, git-ignored SCRIPT.md |

## Product sessions (UI work outside the M-series)

| ID | What | Status | Note |
|---|---|---|---|
| S1 | Readability: light theme default, theme toggle, 14px minimum type, CSS colour tokens | ☑ | PR #15 |
| S2 | Citizen / Expert view, plain-language citizen pages, what-if explanations; Lenis smooth scroll and fades | ☑ | PR #15 |
| S3 | Assistant everywhere (floating button, Home ask bar), plain-language answers, usage limits | ☑ | PR #16 |
| S4 | Assistant on OpenAI `gpt-5-mini` (Groq fallback), status endpoint, site context ("Ask about this site") | ☑ | PR #15 |
| S5 | Citizen reports + gamification | ◐ | Plan in `docs/S5-citizen-reports-plan.md`. Phase 1 (foundation: database layer, sign-in token check, profiles, sign-in UI) built and verified end to end against a real Neon project locally (sign-up, nickname, reload; my API accepts the real token). Phase 2 (reports: checklist form, saving, nickname required, daily limit of 10, a separate unverified map layer of hollow rings, a reports list on each site page, 20 labelled sample reports seeded once) built and checked in a real browser against Neon. Phase 3 (AI note tidy-up with personal-detail warnings, optional photo stored privately in the Neon bucket after a resize and AI check; flagged or unchecked photos hold the report for review) built and checked against real OpenAI and the real bucket. Phase 4 (points ledger and rules with daily and per-site caps, streaks, weekly challenge, 7 badges recomputed from the ledger, reversal, leaderboard by scope and city, My streams page) built and checked in a real browser. Phase 5 (flag button and a hold at three flags, moderator queue with approve and hide that calls the points hooks and deletes photos, a decision log, FHIR export validated with 0 errors (D44), privacy note, delete-my-account, sweep of abandoned uploads) built and checked end to end in a real browser. Moderators are rows in the `moderators` table (no Render setting, no verified email needed); `ADMIN_EMAILS` still works as a second route. Reports never change the model score |
| S6 | Heat-glow map; MapLibre worker bundling fix for production | ☑ | PR #17 |
| S7 | Housekeeping: this file, FHIR badge honesty, Explore empty state, city chips, stale tests | ☑ | this PR |


## Agent sourcing tasks (SOURCING.md — fresh session each) — PAUSED (D33)

Prototype now uses illustrative data. These tasks are optional upgrades: any row sourced later replaces its illustrative value automatically. Do not run sourcing sessions in parallel (IP rate-limits).

Needs M02/M03 loaders (with the new columns) to exist first, so the files have the right shape.

| ID | Task | Prompt | Status | Note |
|---|---|---|---|---|
| A1 | Drug params: carbamazepine | S2 | ☐ | |
| A2 | Drug params: atenolol | S2 | ☐ | |
| A3 | Drug params: losartan | S2 | ☐ | |
| A4 | Drug params: irbesartan | S2 | ☐ | |
| A5 | Drug params: paracetamol | S2 | ☐ | |
| A6 | Drug params: citalopram | S2 | ☐ | |
| A7 | Consumption: PT | S3 | ☐ | |
| A8 | Consumption: IT | S3 | ☐ | |
| A9 | Consumption: FR | S3 | ☐ | |
| A10 | Consumption: BE | S3 | ☐ | |
| A11 | Consumption: NO | S3 | ☐ | |
| A12 | Verifier pass over all rows | S4 | ☐ | Must be a different session from A1–A11 |
| A13 | Resolve CONTEXT §8 open verifications | — | ☐ | Research session; results go to CONTEXT §4 |
| A14 | Auto-place sites | S5 | ☐ | After M05 raster reader |
| A15 | Draft email to R1 corresponding author for Tables S1/S2 | — | ☐ | Save to docs/email_draft.md |

## Human gates (only you)

| ID | Task | Status | Note |
|---|---|---|---|
| H1 | Confirm Devpost registration + team | ☐ | Team required by rules |
| H2 | Review `docs/sourcing_report.md`: all PNEC rows + 5 random others → mark `verified=human`, approve | ☐ | ~20 min |
| H3 | Open `sites_preview.html`, reject bad points, re-run with `--exclude` | ☐ | ~10 min |
| H4 | Send the drafted email (A15) from your address | ☐ | |
| H5 | Record demo video | ☐ | After M24 |

## Next up

1. **Live check** After merging, confirm the live FHIR tab shows the green validation badge (needs the release snapshot deployed).
2. **S5** Citizen reports + gamification, and **M23** CI.

## Last session

T2 FHIR validation (branch `T2-fhir-validator`):
Ran the official HL7 validator on all bundles against the OneAquaHealth IG (compiled from FSH source at a pinned commit; the
IG has no published package, and the old script's package URL 404s). First run found real problems, now fixed: no `fullUrl` on
entries, a guessed Location profile URL that does not exist, predictions missing the `performer` and `effective[x]` the
profile requires, an undefined extension, tags without a code system, and ids with underscores. Result: 0 errors, 1,513
warnings (best-practice). Added `scripts/validate_fhir.py` (`make fhir-validate`), the pure summarising logic with tests, and
the badge now shows the recorded run. Engine 203, api 54, web 28 pass.

T1 engine end to end (branch `T1-engine-end-to-end`):
Downloaded GHS-POP (the fetch script had wrong URLs and tile maths) and computed real populations for the 105 sites
(0.3 s; the old code stitched all tiles per site). Added the `illustrative` status (D33/D36) with labelled placeholder
values, fixed exporter metadata (dev_placeholders was hard-coded false; param_count was the result count), and added
`run/build/fhir/freeze/checks` commands. Ran the engine (630 results, all tiers present), froze it
(`predictions-frozen-illustrative-v1`), ran the checks (C3, C4 fail on illustrative inputs), built the FHIR bundles, fixed
the fhir_index contract drift, and found the API defaulted to the wrong data folder. Tests: engine 189, api 53, web 28 pass.

(Previous: M13–M16.)
Built M13–M16 (FHIR + API):
M13: 4 terminology files in fhir/terminology/ (CodeSystem-observation-category,
CodeSystem-components, CodeSystem-consumption, ValueSet-observation-category).
M14: fhir/builder.py — Location (with OAH Location profile), Group, Consumption
Observation, Prediction Observation (with OAH profile, 6 components, derivedFrom
consumption). Reference Observations moved to checks/fhir_obs.py (separation rule).
build_all() accepts ref_obs list and writes all 8+ bundles + fhir_index.json. 18 tests.
M15: fhir/validator/validate.sh (downloads validator_cli.jar if absent), infra/docker-compose.yml
(HAPI R4 + api service), scripts/load_hapi.py (collection→transaction, POST to HAPI).
M16: FastAPI app in api/. data.py (JSON loader with lru_cache, draws.bin reader).
Routes: core (health/meta/sites/results/checks/methodology/glossary/provenance/draws.bin),
scenario (D13 RQ' = RQ·mλ·mC/mQ), fhir (index + bundle). 15 API tests.
172 engine tests + 15 API tests all pass. Branch: fhir-api.

(Previous: Built M11+M12 — exporters, freeze, consistency checks):
`export_build()` in `export.py` runs all 3 ablation variants, writes results.json
(Pydantic-validated), draws.bin (float32 LE), draws_index.json, sites.json,
provenance.json, methodology.json, glossary.json. `freeze.py` checks dirty tree,
runs strict mode, SHA-256-hashes results.json, writes FROZEN.json, then git-commits
and tags (`predictions-frozen-v1` or `-illustrative-v1` per D36). Fixed bug in
`montecarlo.from_paths`: `load_consumption` returns a dict; now converts to list
with `.values()` before passing to RunContext.
M12 checks: `checks/observed.py` (only observer-reader), `checks/run.py` (C1–C5),
`test_separation.py` (greps pharmashed/ outside checks/ for 'observed'/'rodrigues').
154 engine tests pass (was 123). Branch: `pipeline-output`.

(Previous: Built M04 (sites and streams)): `data/sites/sites.geojson` ships 45 synthetic
sites (9 per city: TLS/GNT/BNV/CBR/OSL) hand-placed on real urban waterways
(Hers-Mort, Touch, Garonne, Schelde, Leie, Calore, Sabato, Mondego, Ceira,
Akerselva, Alna, Lysaker). `engine/src/pharmashed/sites.py`: `cities()` returns
the five static City objects (D02); `load_sites(path)` parses GeoJSON
FeatureCollection, validates id uniqueness, prefix-city match, known city,
point-in-bbox, and size_class. CLI: `pharmashed sites check`. 21 new tests in
`engine/tests/test_sites.py`; 83 total pass. `scripts/fetch_streams.py`:
Overpass query for stream/ditch/canal/river within city bboxes → `streams.geojson`
(simplified 0.0001°, ODbL attribution); run separately (needs network).
`scripts/auto_place_sites.py`: rule-based placement per SOURCING.md S5 with
M05 population hook stubbed (falls back to index-thirds strata until M05 lands).
`population_buffer` is 0 / `pop:pending-m05` throughout — M05 fills real values.

(Previous session built M03 (consumption data): `data/consumption/consumption.csv` ships as
30 `todo` rows (5 countries x 6 drugs) with the M03 columns (granularity,
group_value, molecule_share, share_source_url) plus the sourcing columns
from `SOURCING.md`. `engine/src/pharmashed/consumption.py`: `ConsumptionRow`
(validates sourced rows: source_url+note required, granularity required,
molecule rows need ddd_per_1000_per_day > 0, downscaled rows need
group_value > 0 + molecule_share in (0,1] + share_source_url),
`_check_shares_not_copied` (rejects the same molecule_share +
share_source_url reused across two countries for one drug — SOURCING.md
S3's "never one share across countries"), `load_rows`, `load_consumption`
(strict raises `UnsourcedConsumptionError` listing every `todo` row; dev
returns rows as-is), `consumption_value`, `provenance_entries`. CLI:
`pharmashed consumption check [--strict]`, wired into `make data-check`.
`engine/tests/test_consumption.py` (21 tests). `make test` passes (62
python tests, 1 web test); ruff clean. Strict mode fails on the shipped
file as expected (all 30 rows still need sourcing via A7-A11).

(Previous session built M02 (parameter registry): `data/params/drug_parameters.csv`
ships as 42 `todo` rows (6 drugs x 7 params) with the sourcing columns from
`SOURCING.md` (evidence_quote, retrieved_at, verified, verify_note); `R`
rows carry the "not required: w=0" note per D27. `data/params/priors.yaml`
transcribed verbatim from IMPLEMENTATION.md M02 (locked decisions D04-D06,
not sourced data). `engine/src/pharmashed/params.py`: `ParamRow` (validates
sourced rows: source_url+note required, fe/R in [0,1], ddd_g/pnec/lod > 0,
min<max), `Dist.sample()` for all 4 distribution kinds, `load_drug_params`
(dev mode falls back to `contracts/fixtures/dev_placeholders.yaml` and
flags `dev_placeholders_used`; strict mode raises `UnsourcedParameterError`
listing every non-`R` `todo` row), `load_priors`, `provenance_entries`.
CLI: `pharmashed params check [--strict]`, wired into `make data-check`.
Strict mode fails on the shipped file as expected (36 rows still need
sourcing via A1-A6) — that's correct, not a bug.)

(Full history of M00/M01 sessions is in git log; `docs/PharmaShed.md` v0.2
is still an open blocker, see Blockers below.)

## Follow-ups (cross-module notes)

- **Demo numbers (resolved, D42):** the app now serves real engine output (`make build`, `make freeze`, `make checks`) instead of `scripts/gen_rich_fixtures.py` fixtures. Inputs are still illustrative. Regenerate with: `uv run pharmashed build`, then (clean tree) `uv run pharmashed freeze`, `uv run pharmashed checks`, `uv run pharmashed fhir`.
- **Deployment data (code done, one manual step):** `data/release/` is a committed snapshot of the frozen run (`make release`, `scripts/make_release.py`, compact JSON, 5 MB). The API falls back to it when `data/build/` is absent, and `render.yaml` sets `PHARMASHED_DATA=data/release`. If the Render service was not created from the blueprint, set `PHARMASHED_DATA` to `data/release` in the dashboard (before this the live API served the old hand-made fixtures: `n_draws` 10,000, generated 2026-09-18) and confirm `/api/meta` shows `frozen_tag: predictions-frozen-illustrative-v1`. Re-run `make release` and commit after any new freeze.
- Site auto-placement used index-thirds strata because population was pending; with real GHS-POP available it could be re-run with the population strata from SOURCING.md S5.
- **Contract drift (resolved):** `fhir_index` schema, pydantic model and TS types now include the optional OAH example fields and the fixture uses the schema's `query_demo` shape; the FHIR tab reads the real per-category counts (it used to show 663 for both).
- **Validator (done) / HAPI (not run).** `scripts/validate_fhir.py` (`make fhir-validate`) validates every bundle and records the result; re-run it, then `make release`, after any rebuild of the bundles (a rebuild resets validation to unknown). The local HAPI FHIR server has not been run (Docker Desktop was off).
- `make fhir-validate` and `make api` are still `TODO` stubs in the Makefile (`run`, `fhir`, `freeze`, `checks` and `release` are real).
- `uv run pytest engine api` in one command fails at collection (both `tests/` folders are packages: "No module named tests.test_api"); run `uv run pytest engine` and `uv run pytest api` separately. `make test` was not checked.
- Deployment: `OPENAI_API_KEY` is set on Render (the live `/api/assistant/status` reports `openai` / `gpt-5-mini`). The free tier sleeps, so wake the API before a demo. Assistant limits are in memory and reset on restart.
- `suggestion.md` and `SCRIPT.md` are local and git-ignored.

## Blockers

- `docs/PharmaShed.md` (concept doc v0.2, referenced by CONTEXT.md §2 and
  the M00 build steps) does not exist anywhere found on disk. Needs to be
  supplied by a human before M00's doc-copy step can be completed; do not
  let a coding agent write this from scratch since it would be inventing
  the concept doc, not transcribing a cited source.
