# JUDGEMENT.md — implementation judgment calls

Small in-module calls that aren't big enough for a `CONTEXT.md` §4 D-number
(those are locked project decisions) but aren't obvious from reading the
code either -- the *why* behind a choice, so a fresh session doesn't
re-litigate it or quietly diverge from it. Read alongside `CONTEXT.md` and
`CHECKPOINT.md` at the start of a session; skim only the entries for the
module you're touching.

Append a short entry when you make a call like this. Never delete an entry;
if a later session overturns one, add a new entry that says so and leave
the old one for context.

---

## M00 — Repo scaffold

- Removed `oxlint` (Vite's default scaffold linter) in favour of
  `eslint` + `typescript-eslint` + `eslint-config-prettier`, to match A2's
  toolchain table exactly rather than carrying two linters.
- `docs/PharmaShed.md` (concept doc v0.2) could not be found anywhere on
  disk during scaffolding. Left uncopied rather than written from scratch
  (writing it would mean inventing the concept doc). Still open — see
  CHECKPOINT.md Blockers.
- `data/observed/observed_rodrigues2025.csv` was found in `~/Downloads/`
  (not inside the project) and copied in as-is; treated as a genuine cited
  source (it has `source_ref`/`note` columns), not fixture data.

## M01 — Contracts

- `checks.schema.json`, `methodology.schema.json`, `provenance.schema.json`
  and `fhir_index.schema.json` only had a one-line description each in
  IMPLEMENTATION.md's M01 section (only `sites.json`/`results.json` had
  worked examples). Their shapes were inferred from the later sections that
  actually use them (M12 for checks, M13-M15 for fhir_index, M21/M22 for
  methodology and the FHIR tab). If those later modules turn out to need a
  different shape, the schemas should move, not the modules.
- `checks.schema.json`'s per-check `data` field is left as a bare
  `type: object` (no sub-schema) since each check (C1-C5) has a different
  payload shape (scatter points, orders+tau, rows, rank-change table). A
  discriminated union keyed on `id` would be more precise but adds a lot of
  schema for a payload that's read almost entirely by hand-built chart
  components, not validated field-by-field.
- `scripts/make_fixtures.py` uses `N_STORED = 64` for the fixture
  `draws.bin`, not the real `N_STORED = 1000` (CONTEXT D12). Fixtures are
  for shape-testing, not realism; keeping them small keeps the repo light.
- TS types are generated as one concatenated `web/src/types/contracts.ts`
  (via a small custom `compile()` loop in `web/scripts/gen-types.mjs`)
  rather than one file per schema, to match the literal file name
  IMPLEMENTATION.md's M01 acceptance criteria names.

## M02 — Parameter registry

- `ParamRow` treats empty-string fields as absent via a
  `model_validator(mode="before")` on the model itself, not by pre-cleaning
  rows in the CSV loader. That way any caller (the loader, a test building
  a row by hand, a future sourcing-agent script) gets the same tolerant
  parsing for free, instead of every caller needing to know the blank-string
  convention.
- `provenance_entries()` takes explicit `(rows, priors)` arguments rather
  than IMPLEMENTATION.md's zero-argument sketch (`def provenance_entries()
  -> dict[str, ProvenanceEntry]`). The sketch can't work without data; the
  zero-arg form was read as illustrative, not literal.
- `contracts/fixtures/dev_placeholders.yaml` uses **one shared fallback
  block** for any `todo` row, not 42 per-drug fake rows. Dev placeholders
  exist to make the pipeline runnable, not to be per-drug realistic --
  matches the "obviously fake" framing in CONTEXT A5.
- The CLI (`pharmashed params check`) uses stdlib `argparse`, not a
  third-party CLI framework (click/typer), since M02 only needed one
  subcommand and the toolchain table (A2) doesn't name a CLI library.
- `R` (WWTP removal) rows are excluded from the strict-mode "unsourced"
  count, per D27 (`w=0` for every MVP site makes `R` unused by the model
  equations in A4).
