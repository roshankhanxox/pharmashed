# SOURCING.md — agent protocol for parameters, consumption and sites

Agents research and fill the data files; a second agent verifies; a human reviews a generated report. No value enters `drug_parameters.csv` or `consumption.csv` without a **verbatim evidence quote** from the cited source.

Load only the section you need: `sed -n '/^## S2/,/^## S3/p' SOURCING.md`

---

## S0 — Roles and flow

```
Researcher session (one drug or one country per session)
   → writes rows: value + source_url + source_note + evidence_quote + retrieved_at, verified=none
Verifier session (fresh context, never the same session as the researcher)
   → re-fetches every URL, checks the quote exists and contains the value, checks units/conversion
   → sets verified=agent or verified=failed (with reason)
make sourcing-report
   → docs/sourcing_report.md: one table row per value with quote + link + verifier status
Human review (~20 min)
   → read all PNEC rows + 5 random others; mark verified=human on the ones checked; approve
Only then: make run-strict → make freeze
```

**Evidence rules (apply to every row):**
1. `evidence_quote`: verbatim text from the source that contains the number, under 40 words. Shorten with "…" if needed, but the number must appear.
2. `source_note`: where in the source (table/section/page) plus any conversion ("mg → g", "% → fraction").
3. `retrieved_at`: ISO date.
4. If no source is found after a reasonable search, leave `status=todo` and set `source_note="not found: <what was tried>"`. **Never** fill from memory or estimate.
5. If sources disagree, use a range (`uniform` or `loguniform`) and cite both in `source_note`.
6. Paywalled or unfetchable sources: note "needs manual" and move on.

---

## S1 — Selection rules (turn judgment into rules)

Agents follow these rules instead of choosing freely. If a rule can't be applied, record why and stop for human input.

| Param | Rule |
|---|---|
| `atc` | WHO ATC/DDD Index (atcddd.fhi.no). Code for the plain oral product |
| `ddd_g` | WHO ATC/DDD Index, oral route, converted to grams, `fixed` |
| `fe` | Fraction excreted **unchanged** (urine + faeces if both reported). Priority: peer-reviewed PK review or regulatory label (EMA SmPC / FDA label) > DrugBank. Range across sources → `uniform` |
| `R` | **Not required for MVP** (all sites w=0). Leave `status=todo`, `source_note="not required: w=0 for all MVP sites"`. The loader treats it as optional when all sites have w=0 |
| `k_per_h` | In-stream attenuation rate from field studies; start from Acuña et al. 2015 (Sci Total Environ 503–504:133–141). If only half-life or distance given, record the conversion used to derive `k_per_h` in `source_note`. If not found for a drug → `todo` |
| `pnec_ng_l` | NORMAN Ecotoxicology Database: freshwater PNEC ("lowest PNEC" record) with its ID. Fallback: EU Watch List / JRC dossier freshwater PNEC. Record which source type was used. **Always human-reviewed** |
| `lod_ng_l` | From R1's analytical method reference: Pereira et al. 2023, Appl. Sci. 13(11):6414. Only that source (it's the method the observations used) |
| consumption | National molecule-level source first (see S3). Fallback: OECD group-level × country-specific molecule share, with the share's source cited separately |

---

## S2 — Researcher prompt: drug parameters

Run once per drug, in a fresh session:
```
Read CONTEXT.md and SOURCING.md sections S0, S1, S2 only.
Research drug <DRUG> for data/params/drug_parameters.csv: params atc, ddd_g, fe, k_per_h, pnec_ng_l, lod_ng_l
(R is not required — mark as instructed in S1).
Use web search and fetch. For every value, fill source_title, source_url, source_note,
evidence_quote (verbatim, contains the number), retrieved_at; set verified=none.
Follow S1 selection rules strictly. If not found, status=todo with what you tried.
Edit only this drug's rows. Then append a 3-line summary to CHECKPOINT "Last session".
```

## S3 — Researcher prompt: consumption

Run once per country, in a fresh session:
```
Read CONTEXT.md and SOURCING.md sections S0, S1, S3 only.
Research country <CC> for data/consumption/consumption.csv: DDD per 1000 inhabitants per day
for the six drugs in CONTEXT D01, most recent year available.
Priority: national molecule-level statistics; fallback OECD group level × a country-specific
molecule share from a cited national source. Record granularity per row.
Every row needs source_url, source_note, evidence_quote (verbatim), retrieved_at; verified=none.
Sources may be in Portuguese, Italian, French, Dutch or Norwegian — quote the original text
and translate in source_note. If a download (xlsx/csv) is needed, save it under data/raw/
and cite the sheet/row. Edit only this country's rows. Then update CHECKPOINT.
```
Candidate national sources (to verify, not assume): Norway public drug statistics; France ANSM / Medic'AM; Italy AIFA OsMed report; Belgium INAMI-RIZIV; Portugal Infarmed.

## S4 — Verifier prompt

Run in a fresh session after researchers finish (can batch all rows):
```
Read CONTEXT.md and SOURCING.md sections S0, S1, S4 only.
For every row in data/params/drug_parameters.csv and data/consumption/consumption.csv with verified=none:
1. Fetch source_url. 2. Confirm evidence_quote appears (allow whitespace/formatting differences).
3. Confirm the number in the quote matches the value after the conversion stated in source_note.
4. Confirm the row follows the S1 rule for its param.
Set verified=agent if all pass, else verified=failed and write the reason in verify_note.
Do not change values. Do not research alternatives. Then run `make sourcing-report` and update CHECKPOINT.
```

## S5 — Sites (auto-placement, replaces manual placement)

Implemented as `scripts/auto_place_sites.py`:
1. Overpass query per city bbox: `waterway` in {stream, ditch, canal}; exclude `tunnel=culvert` and any segment shorter than 200 m.
2. Candidate points every 150 m along lines.
3. Stratify candidates by GHS-POP density within 500 m (tertiles: outskirts / mid / centre); choose 3 per stratum spread apart by ≥ 800 m → 9 sites per city (seeded).
4. `size_class` rule: OSM `width` tag if present (S < 2 m, M 2–5 m, L > 5 m); else `ditch`→S, `stream`→S, `canal`→M.
5. Write `sites.geojson` and `sites_preview.html` (a Leaflet map).
6. Human: open the preview, reject obviously bad points (underground, private canal), re-run with excluded ids. Rule-based placement is documented as such in the Methodology page.

## S6 — Report

`make sourcing-report` → `docs/sourcing_report.md` with columns: file, drug/country, param, value, unit, evidence_quote, source link, verified status, verify_note. Counts at the top: sourced / todo / verified=agent / verified=human / failed.
