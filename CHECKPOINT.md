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
| M03 | Consumption data | ☐ | Code only; values = agent tasks A7–A11 |
| M04 | Sites + streams | ☐ | Placement = agent task A14 |
| M05 | Population (GHS-POP) | ☐ | |
| M06 | Priors + sampling | ☐ | |
| M07 | Model core | ☐ | |
| M08 | Monte Carlo runner | ☐ | |
| M09 | Sensitivity + flips | ☐ | |
| M10 | Scoring + ranking | ☐ | |
| M11 | Exporters + freeze | ☐ | Freeze needs strict mode |
| M12 | Consistency checks | ☐ | Needs freeze |
| M13 | FHIR terminology | ☐ | |
| M14 | FHIR builder | ☐ | |
| M15 | Validator + HAPI | ☐ | |
| M16 | API | ☐ | |
| M17 | Assistant | ☐ | Needs API key |
| M18 | Web shell + data layer | ☐ | |
| M19 | Explore tab | ☐ | |
| M20 | Scenarios tab | ☐ | |
| M21 | Consistency + Methodology tabs | ☐ | |
| M22 | FHIR tab + Assistant drawer | ☐ | |
| M23 | CI | ☐ | Grows incrementally |
| M24 | Docs + demo script | ☐ | Last |

## Agent sourcing tasks (SOURCING.md — fresh session each)

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

1. **M03** Consumption data (loader with the sourcing columns)
2. Then run sourcing sessions **A1–A11** (M02/M03 loaders are ready for them), then **A12**
3. **H1** today (registration)

## Last session

Built M02 (parameter registry): `data/params/drug_parameters.csv` ships as
42 `todo` rows (6 drugs x 7 params) with the sourcing columns from
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
`engine/tests/test_params.py` (24 tests) covers every validation rule plus
strict/dev mode. `make test` passes (41 python tests, 1 web test); ruff
clean. Strict mode fails on the shipped file as expected (36 rows still
need sourcing via A1-A6) — that's correct, not a bug.

(Full history of M00/M01 sessions is in git log; `docs/PharmaShed.md` v0.2
is still an open blocker, see Blockers below.)

## Follow-ups (cross-module notes)

_(empty)_

## Blockers

- `docs/PharmaShed.md` (concept doc v0.2, referenced by CONTEXT.md §2 and
  the M00 build steps) does not exist anywhere found on disk. Needs to be
  supplied by a human before M00's doc-copy step can be completed; do not
  let a coding agent write this from scratch since it would be inventing
  the concept doc, not transcribing a cited source.
