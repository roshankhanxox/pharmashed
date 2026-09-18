# CONTEXT.md — read this first, every session

Keep this file short (under ~1,500 words). It is loaded at the start of every coding session. Details live in `IMPLEMENTATION.md` (by module ID) and `docs/PharmaShed.md` (the science).

## 1. Project in five lines

- **PharmaShed**: sampling-priority screening for pharmaceuticals in small urban streams, for the OneAquaHealth IEEE Global Hackathon 2026 (Track 7 Digital Health Standards; secondary Track 6).
- Existing exposure models (ePiE, GREAT-ER) route drug loads via treatment-plant outfalls and predict ~0 for streams without one. PharmaShed adds the **untreated pathway** (sewer leakage, misconnections, overflows).
- Inputs: national drug consumption, cited drug parameters, stated priors. Output: a Monte Carlo **sampling priority score** per site × drug, sensitivity drivers, and "what flips this site" multipliers.
- Results are published as FHIR resources aligned with the OneAquaHealth IG; a tool-only assistant explains them.
- Honest framing: screening under stated assumptions; consistency checks against Rodrigues et al. 2025, not validation.

## 2. Document precedence

`CONTEXT.md` §4 decisions **>** `IMPLEMENTATION.md` **>** `docs/PharmaShed.md` (v0.2). If a later decision changes something, add it to §4; do not silently edit the older docs.

## 3. Repo map (one line each)

| Path | What |
|---|---|
| `contracts/` | JSON Schemas + fixtures — **the** data contract (M01) |
| `data/params/` | `drug_parameters.csv` (cited), `priors.yaml` (M02) |
| `data/consumption/` | `consumption.csv` (cited) (M03) |
| `data/sites/` | `sites.geojson` (hand-placed synthetic), `streams.geojson` (M04) |
| `data/observed/` | `observed_rodrigues2025.csv` — **only `checks/` may read it** |
| `data/build/`, `data/frozen/` | engine outputs; frozen = tagged predictions |
| `engine/src/pharmashed/` | Python engine M02–M14 (`checks/` = M12, `fhir/` = M14) |
| `fhir/` | terminology JSON (M13), validator script, generated bundles |
| `api/` | FastAPI + assistant (M16–M17) |
| `web/` | Vite + React + TS app (M18–M22) |
| `infra/` | docker-compose for HAPI |
| `SOURCING.md` | agent protocol for sourcing parameters, consumption and sites |
| `JUDGEMENT.md` | log of small in-module implementation calls, per module |

Module lookup: `sed -n '/^## M07/,/^## M08/p' IMPLEMENTATION.md`

## 4. Locked decisions log

Add new decisions at the bottom with the next number. Never delete; mark superseded ones instead.

| # | Decision |
|---|---|
| D01 | Six drugs: carbamazepine, atenolol, losartan, irbesartan, paracetamol, citalopram. Paracetamol = "acetaminophen" in the observed CSV |
| D02 | Five cities: Toulouse (TLS, FR), Ghent (GNT, BE), Benevento (BNV, IT), Coimbra (CBR, PT), Oslo (OSL, NO) |
| D03 | Sites are hand-placed synthetic points on real streams, 8–10 per city, all `w=0`, `valid=true`, size class S/M/L |
| D04 | λ prior: log-uniform 0.002–0.15 (effective untreated fraction). Barcelona-type leakage is a UI preset (λ×3), not in the prior |
| D05 | Q prior per size class (m³/s, log-uniform): S 0.005–0.1, M 0.02–0.5, L 0.1–2.0. Cap 2 m³/s |
| D06 | κ (stream-condition multiplier) removed from the model. "Riparian restoration" exists only as an illustrative UI slider (user-set removal 0–50%) |
| D07 | No stagnant-site detection; stated as a limitation only |
| D08 | Output name: **sampling priority score** = share of draws with RQ > 1. Never call it a probability of exceedance in the UI |
| D09 | Tiers: high ≥ 0.5, medium ≥ 0.1, else low |
| D10 | Sensitivity = Spearman rank correlation (tornado). No Sobol |
| D11 | No mixture index |
| D12 | N_DRAWS = 10,000 for statistics; N_STORED = 1,000 per pair for client-side scenarios |
| D13 | Scenario math is client-side: `RQ' = RQ · mλ · mC / mQ` (valid because w=0) |
| D14 | Population: GHS-POP 100 m grid, 500 m buffer. It is a proxy for sewer density, not a catchment |
| D15 | Consumption: molecule-level national data preferred; otherwise group × **country-specific** share, flagged per country |
| D16 | Dev mode uses fake placeholders + red banner; strict mode refuses `todo` rows; freeze requires strict |
| D17 | FHIR: predictions are `Observation` with the IG profile `observation-with-component-oah`, category `model-prediction` from our own CodeSystem, components for PEC p05/p50/p95, RQ p50, score, LOD share. No `RiskAssessment` |
| D18 | FHIR builder in Python (`fhir.resources`); Java only for the HL7 validator. A Java builder is an optional swap |
| D19 | HAPI FHIR runs locally via docker-compose only; the hosted demo serves bundles as static JSON |
| D20 | Assistant tools: list_priority_sites, get_site_profile, explain_drivers, run_scenario, get_provenance. No raw FHIR query tool. Eval set of 12–15 questions |
| D21 | Web: Vite + React + TS + Zustand + MapLibre + Tailwind + hand-written SVG charts. Desktop only |
| D22 | Web tabs: Explore · Scenarios · Consistency · Methodology · FHIR, plus the Assistant drawer and an always-visible footer strip |
| D23 | Consistency checks C1–C5 exactly as defined in IMPLEMENTATION.md M12 (pre-registered). C4: observed city max vs max over city sites of predicted p95; pass if observed ≤ predicted ≤ 10× observed |
| D24 | Ablation variants: full, pop_only, wwtp_only (the last shows the ePiE-like blind spot: PEC = 0) |
| D25 | No local LLM in scope. Assistant model from env `ASSISTANT_MODEL` |
| D26 | Data sourcing is agent-driven per `SOURCING.md`: researcher → separate verifier → human review of `docs/sourcing_report.md`. Freeze requires all sourced rows verified; all PNEC rows human-verified |
| D27 | `R` (WWTP removal) is not required for the MVP because every site has w=0; the loader treats it as optional in that case |
| D28 | Sites are auto-placed by rules (SOURCING.md S5), with a human preview/reject pass. Replaces manual placement in D03 (the other D03 terms still hold) |

## 5. Hard rules (never break)

1. **Never invent a scientific number.** Drug parameters and consumption values are sourced only via the `SOURCING.md` protocol: a fetched source, a verbatim `evidence_quote` containing the number, then an independent verifier session. Never from memory. In a normal coding session (not a sourcing session), leave such values `todo`.
2. **Never read `data/observed/` outside `engine/src/pharmashed/checks/`.**
3. **Never** call the score a probability, or state that a stream is safe or unsafe.
4. Contracts first: if a data shape changes, update the schema in `contracts/`, regenerate fixtures and types, and log it in §4.
5. Every module ends with its acceptance tests passing and a CHECKPOINT update.
6. Keep changes inside the module being worked on; if another module needs a change, note it in CHECKPOINT "follow-ups" instead of doing it.

## 6. Key facts from the paper (for code and copy)

Rodrigues et al. 2025, J. Hazard. Mater. 499:139946: 102 sites, 5 cities, one grab sample each (Nov 2022–Sep 2023); 20 drugs analysed, 16 detected; 91% of sites with any drug, 79% with mixtures; city total order TLS > GNT > BNV > CBR > OSL (CBR ≈ OSL). Irbesartan 73% detection, max 31,659 ng/L (TLS), 7,420 (BNV), 1,690 (CBR). Paracetamol max 16,789 (GNT), 788 (OSL); detection 31% overall. Carbamazepine 58%. Full table: `data/observed/observed_rodrigues2025.csv`.

## 7. Glossary (use these exact names in UI and assistant)

| Symbol | Plain name |
|---|---|
| PEC | predicted concentration |
| PNEC | no-effect threshold |
| RQ | risk ratio (PEC ÷ PNEC) |
| LOD | detection limit |
| λ | leakage (untreated fraction) |
| Q | stream flow |
| τ | travel time |
| k | in-stream loss rate |
| fe | fraction excreted unchanged |
| DDD | defined daily dose |
| score | sampling priority score |

## 8. Open verifications (resolve, then move to §4)

- [ ] Does the OneAquaHealth IG define a Location profile? What is the working validator command for the CI-build IG?
- [ ] GHS-POP current release name, tile scheme and download URL
- [ ] Which national sources give molecule-level DDD for PT, IT, FR, BE, NO (licence + format)
- [ ] LOD per drug from R1's method reference (Pereira et al. 2023, Appl. Sci. 13(11):6414)
- [ ] GREAT-ER primary citation (candidate: Feijtel et al. 1997, Chemosphere 34(11)) — verify before adding to docs
- [ ] Basemap tile provider terms for the demo
