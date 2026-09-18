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
| M00 | Repo scaffold | ☐ | |
| M01 | Contracts + fixtures + types | ☐ | Unblocks all web work |
| M02 | Parameter registry | ☐ | Code only; values = human task H2 |
| M03 | Consumption data | ☐ | Code only; values = human task H3 |
| M04 | Sites + streams | ☐ | Placement = human task H4 |
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

## Human tasks (not for the coding agent)

| ID | Task | Status | Note |
|---|---|---|---|
| H1 | Confirm Devpost registration + team | ☐ | Team required by rules |
| H2 | Source 42 rows of `drug_parameters.csv` (DDD, fe, R, k, PNEC, LOD, ATC) with URLs + notes | ☐ | **Critical path to freeze** |
| H3 | Source 30 rows of `consumption.csv` (5 countries × 6 drugs) | ☐ | **Critical path to freeze** |
| H4 | Hand-place 8–10 sites per city with size class | ☐ | See `scripts/place_sites.md` |
| H5 | Email R1 corresponding author for Tables S1/S2 | ☐ | Address on the paper's first page |
| H6 | Resolve CONTEXT §8 open verifications | ☐ | |
| H7 | Record demo video | ☐ | After M24 |

## Next up

1. **M00** Repo scaffold
2. **M01** Contracts + fixtures (then web M18 and engine M02 can proceed in parallel)
3. Start **H2/H3/H4** in parallel (human)

## Last session

_None yet. Planning docs created: IMPLEMENTATION.md, CONTEXT.md, CHECKPOINT.md, docs/PharmaShed.md v0.2, data/observed/observed_rodrigues2025.csv._

## Follow-ups (cross-module notes)

_(empty)_

## Blockers

_(none)_
