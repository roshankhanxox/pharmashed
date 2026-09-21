# PharmaShed — Demo Script
> Second monitor only. Speak at 70% of your normal pace.
> Pause after every number — let it land. [PAUSE] cues are mandatory beats.
> Target: 10–11 minutes. Move between tabs deliberately — never rush a transition.

---

## THE HOOK (0:00 – 1:30)
**Camera only. App not open yet.**

> "Here's a problem nobody talks about.
>
> You're an environmental officer. Your job is to monitor pharmaceutical pollution
> in urban streams — rivers running through city centres, catchment tributaries,
> the water that ends up in reservoirs. You have a sampling kit, a car, and a budget
> for maybe eight site visits this month. There are a hundred sites on your list.
>
> Which eight do you go to?
>
> Right now — the honest answer is gut feeling. Maybe the sites you visited last year.
> Maybe wherever the complaints came from. Maybe you triangulate from wastewater plant
> records — but that only works when there's a treatment plant on the stream you're
> studying.
>
> There is no tool that tells you, before you leave the office, which stream is most
> likely to have a risk ratio above regulatory thresholds — for which drug, at what
> concentration, under what hydrological conditions.
>
> That's not a niche gap. In 2025, Rodrigues and colleagues published a European field
> study in the Journal of Hazardous Materials — 102 urban stream sites, five cities,
> 20 pharmaceuticals screened. [PAUSE]
> Ninety-one percent of sites had detectable drug concentrations.
> Seventy-nine percent had mixtures.
> The highest irbesartan reading was 31,659 nanograms per litre in Toulouse. [PAUSE]
>
> Not a single one of those 102 sites had a wastewater treatment plant directly on
> the stream. So every established screening tool — ePiE, GREAT-ER — would have
> predicted concentration of approximately zero at every one of them.
>
> That's the gap. And this is the tool that closes it."

*(Open `pharmashed.roshankhan.me` — Home tab visible)* [PAUSE]

> "PharmaShed was built for the IEEE OneAquaHealth Hackathon — the initiative that is
> trying to bring clinical and environmental health data into the same interoperability
> standard. That's why everything it produces is FHIR R4. But let me show you the
> science first."

---

## HOME TAB — The Problem (1:30 – 2:10)
**Scroll slowly down the Home tab. Don't rush.**

> "The standard exposure models — ePiE and GREAT-ER — work like this.
> A drug is prescribed. The patient excretes a fraction of it. That fraction
> enters the sewer. The sewer leads to a wastewater treatment plant.
> The WWTP removes some of it. The effluent discharges into the receiving water.
>
> That's the model. It's well-designed. It works."

*(Point at the red 'ePiE / GREAT-ER: PEC ≈ 0' box on screen)*

> "The problem is the starting assumption. If there is no WWTP on the stream —
> and in our five-city dataset, there isn't one at any of the 105 monitoring sites —
> the model has no load pathway to route. [PAUSE]
> Predicted concentration: approximately zero. At all 105 sites. Every single one.
>
> That's not a model failure. That's the model doing exactly what it was designed
> to do. It just wasn't designed for this type of stream.
>
> The Rodrigues study found irbesartan at 7,420 ng/L in Benevento.
> ePiE predicts zero there. Both are technically correct. That's what a scope gap
> looks like."

---

## HOME TAB — The Architecture Diagram (2:10 – 3:20)
**Scroll to the 'Data flow & architecture' diagram.**

> "PharmaShed adds one thing the standard models don't have."

*(Point at the highlighted indigo box — 'The innovation — untreated pathway')*

> "Lambda. The leakage fraction.
>
> In any urban sewer network, a fraction of wastewater bypasses treatment entirely —
> sewer exfiltration through cracked pipes, deliberate misconnections, combined sewer
> overflows during rainfall. That fraction goes directly into the stream without
> treatment.
>
> We model it as lambda — a log-uniform prior between 0.2% and 15%. [PAUSE]
>
> Why log-uniform? Not uniform? Because the literature puts city-wide exfiltration
> at roughly 0.5 to 3 percent of dry-weather flow — that's Fenz et al. 2005 and the
> APUSS project. But local hotspots near misconnections or old combined systems can
> reach 10 to 15 percent. A log scale covers that spread without over-weighting
> either tail. A flat uniform prior would put too much mass on the high end."

*(Point at the Monte Carlo engine box)*

> "Here is the full equation. [PAUSE]
>
> PEC — predicted environmental concentration — equals population times DDD
> times lambda, divided by Q. [PAUSE]
>
> Population: the catchment size. DDD: the defined daily dose, the WHO standard
> unit for drug consumption. Lambda: the leakage fraction. Q: river flow.
> That ratio gives concentration. Divide by PNEC — the regulatory no-effect
> threshold — and you have the risk quotient RQ.
>
> Why put the prior directly on Q, rather than sampling width times depth
> times velocity separately? Because sampling hydraulic variables independently
> produces impossible streams — a 10-centimetre-wide channel at 2 metres per second.
> We put the prior on Q per stream size class: small streams 5 to 100 litres
> per second, medium 20 to 500. One parameter, one draw, one coherent stream."

*(Point at the Score tier boxes — red, amber, green)*

> "For each of 1,000 draws: draw a lambda, draw a Q, apply consumption
> uncertainty. Compute load. Divide by Q. Divide by PNEC.
> Count how many draws produced RQ above 1. That fraction is the score. [PAUSE]
>
> Score above 0.5: high — red. Above 0.1: medium — amber. Below: green."

*(Click the Explore tab)*

---

## EXPLORE TAB — The Map (3:20 – 3:55)
**The map opens on Toulouse. Don't click anything yet.**

> "105 sites. Five cities. The circles sit on real OpenStreetMap waterways —
> you can see the river network underneath. Every marker is downstream of
> a population centre, near overflow outfalls, where pharmaceutical load
> actually reaches the water."

*(Pan the map, hover a marker to show the tooltip)*

> "Hover over any site and you get the overall priority score and the four
> highest-concern drugs for that site. That's the pre-field briefing —
> before you drive anywhere. [PAUSE]
>
> Let me switch drugs."

**Click `irbesartan` in the drug strip.**

> "Irbesartan — an angiotensin II receptor antagonist, front-line treatment
> for hypertension and diabetic nephropathy. Very tight PNEC — endocrine-active,
> documented effects at low concentrations. Watch the map." [PAUSE]

*(Let it re-render)*

> "More red. Same catchment, same population, same leakage — completely different
> risk profile. The PNEC is what determines whether a concentration is a problem.
> Irbesartan's threshold is one of the tightest in our set."

**Click the highest-scoring red marker.**

> "Open the highest-priority site." [PAUSE]

*(Site inspector opens)*

**Point at the score number.**

> "Sampling priority score: [read it]. [PAUSE]
> In [score × 100]% of our 1,000 simulated draws, predicted irbesartan concentration
> exceeded the regulatory no-effect threshold.
> Not a probability of harm. A priority signal under stated prior assumptions."

**Point at the band chart.**

> "Each row is one drug. The bar is the uncertainty band — 5th percentile left,
> 95th right, median dot centre. The x-axis is nanograms per litre.
> The dashed vertical line is the PNEC. Everything right of that line is a draw
> predicting harm. When the whole bar sits past it — like here — the score is close to 1.
>
> Expand the irbesartan row." [PAUSE]

*(Click it)*

> "Raw simulation output. Every bar is a bucket of log-concentration draws.
> Coloured region: draws where RQ exceeded 1. Count them, divide by total —
> that's the number you just read. No black box. You're looking at the simulation."

*(Click Scenarios tab)*

---

## SCENARIOS TAB (4:30 – 5:10)

**Click `Drought` preset.**

> "Q sits in the denominator. Less water, same load — higher concentration.
> Drought: flow drops to 20% of baseline." [PAUSE]

*(Point at score shifting)*

> "Score jumps. Same site, same drug, same population — just a drier river.
> This is what a climate officer models before a heat event, not after."

**Click `Sewer repair`.**

> "Flip direction. Sewer rehabilitation cuts untreated discharge by half —
> lambda drops 50%. Score falls. [PAUSE]
>
> That number is what an infrastructure team takes into a budget meeting.
> If we invest in this repair, priority drops from high to medium at this site.
> Is it justified? Now they can model it before committing."

**Drag the λ slider.**

> "And you can explore it continuously — every position reruns the score
> live over stored draws. No server call. Float32 arithmetic in the browser
> over 630,000 precomputed draws."

*(Click Methodology tab)*

---

## METHODOLOGY TAB (5:10 – 6:40)
**Scroll through it slowly and deliberately. This is the technical heart of the demo.**

> "The full model specification is in the product — not in a supplementary PDF
> attached to an email. Reviewers can read the pipeline while they use the output."

---

### Model Pipeline diagram

**Point at the pipeline diagram at the top.**

> "The model has four stages. [PAUSE]
>
> Stage one: load estimation. Population times DDD times lambda.
> The DDD — defined daily dose — is the WHO standard unit. We use national
> consumption statistics, not local prescribing data, so the prior carries
> that national-to-local uncertainty explicitly.
>
> Stage two: dilution. Divide load by stream flow Q. Small stream, same load —
> concentration spikes. That's why Q has its own prior and why the drought
> scenario moves the score so much.
>
> Stage three: risk ratio. PEC divided by PNEC. The PNEC is drug-specific —
> irbesartan's is far lower than paracetamol's, which is why switching drugs
> on the map changes the colour pattern completely.
>
> Stage four: scoring. Across 1,000 draws, count the fraction where RQ exceeds 1.
> That fraction is the number on the map marker."

---

### Priors Table

**Scroll to the priors table. Let it be visible for a moment before speaking.**

> "The priors table. Every parameter in the model — its distribution, its range,
> its unit, its status. [PAUSE]
>
> Two statuses matter here.
>
> Green — sourced. That means the value comes from a peer-reviewed source,
> cited and quoted verbatim in the sourcing log. It's auditable.
>
> Yellow — illustrative. That means a deliberately round number, no citation,
> placed here to make the prototype run. The pipeline to replace it is already
> built — the slot is there, the sourcing protocol is written, the format is defined.
>
> What we never do: attach a citation to an illustrative number. That's a rule,
> not a preference. An illustrative value badged as sourced is fraud.
> The badge in the table is a machine-readable signal, not decoration.
> The moment real values replace illustrative ones, the badge changes —
> and the meta.tag on every corresponding FHIR Observation changes with it."

*(Point at a specific row — lambda if visible)*

> "Lambda: log-uniform, 0.002 to 0.15. That range comes from Fenz et al. 2005
> and the APUSS project — city-wide exfiltration at 0.5 to 3% of dry-weather flow,
> local hotspots up to 15%. The log scale covers both without over-weighting extremes."

---

### Identifiability Callout

**Scroll to the amber warning box. Point at it.**

> "This is the intellectually honest part. [PAUSE]
>
> Lambda and Q appear only as a ratio in the PEC equation — load divided by flow.
> A single grab sample cannot tell you whether a high observed concentration
> came from heavy sewer leakage or simply a low-flow day.
> This is a fundamental identifiability constraint. You cannot separate the
> two parameters from one measurement — it's a mathematical impossibility,
> not a data gap you can fill by sampling harder.
>
> PharmaShed doesn't paper over it with a point estimate. We propagate the
> prior uncertainty through every draw and show you the full distribution.
> A tool that gives you a single number here is either using a hidden assumption
> or ignoring the constraint entirely. We think that's the wrong trade-off
> when you're deciding where to deploy a field team.
>
> The score reflects uncertainty under prior assumptions. That is intentional
> and disclosed — it's Decision 8 in the design log."

---

### Ablation — Three Model Variants

**Scroll to the ablation section. Click the `WWTP-only (ePiE baseline)` button.**

> "The ablation. Three model variants, compared step by step. [PAUSE]
>
> Start with WWTP-only. This is the ePiE equivalent — all drug load routed
> via treatment plant outfalls."

*(Point at the red 'no rankings' box that appears)*

> "Nothing. [PAUSE]
>
> Every site in this dataset has w equals 0 — no WWTP on the stream.
> The model has no load pathway to use. Predicted concentration: zero
> at all 105 sites. This isn't a demonstration that ePiE is wrong —
> it's a demonstration of its scope. It was never designed for this class of site.
> PharmaShed is."

**Click `Population only`.**

> "Step two. Add population density — the catchment size within 500 metres.
> No national consumption data, no lambda yet.
>
> Sites near dense urban cores start appearing. The model can now distinguish
> a site in central Toulouse from a rural site outside Oslo.
> But it's flat within a city — everyone in the same population band gets
> the same score regardless of how bad the local sewer infrastructure is."

**Click `Full model`.**

> "Step three. Add lambda — the untreated discharge pathway. [PAUSE]
>
> Now rankings sharpen within cities. Sites near old combined sewer systems,
> near known overflow points, separate from sites with modern infrastructure
> even at similar population density.
>
> The check is whether rankings stay stable as you add each component.
> If they collapse, the component is noise. If they hold and sharpen,
> it's carrying genuine signal. The full model holds.
>
> This is what the Explore map shows — it always runs the full model."

*(Click Consistency tab)*

---

## CONSISTENCY TAB (6:40 – 7:25)

**Scroll through the five checks slowly.**

> "Five pre-registered consistency checks against the Rodrigues field data. [PAUSE]
>
> Pre-registered: predictions were frozen before any comparison was run.
> No tuning after the fact. If the checks pass, it's because the validation
> pipeline is structurally correct — not because we adjusted parameters to fit.
>
> C1: detection share. Does the fraction of sites our model predicts above
> the detection limit match what Rodrigues observed in the field?
>
> C2: city ranking. Does our rank ordering of the five cities match the
> total pharmaceutical load observed? The field study found
> Toulouse, then Ghent, then Benevento, then Coimbra and Oslo roughly tied.
> Does our model recover that? [PAUSE]
>
> C3: concentration order of magnitude. Are our PEC bands within a factor
> of 10 of observed values? Not exact — the parameters are illustrative —
> but in the right ballpark?
>
> C4: cross-drug consistency. Do relative drug rankings hold across cities?
> If irbesartan outranks citalopram in Toulouse, does it in Ghent too?
>
> C5: ablation stability. When you add the lambda component, do the top
> sites stay at the top — or does the ranking collapse? [PAUSE]
>
> These pass because the pipeline is correct.
> The moment real sourced parameters replace illustrative ones,
> these checks run again automatically. That's the design."

*(Click FHIR tab)*

---

## FHIR TAB (7:25 – 9:15)
**This is the interoperability story — the IEEE OneAquaHealth track requirement. Move deliberately.**

---

### The explainer panel

**Point at the 'What FHIR solves here' panel.**

> "FHIR — Fast Healthcare Interoperability Resources — is the HL7 standard for
> exchanging health data. Every hospital, every clinical system, every national
> health authority that has adopted it speaks the same data format. [PAUSE]
>
> The OneAquaHealth Initiative extends that standard to environmental health —
> air quality, water chemistry, pharmaceutical concentrations — using the same
> Observation, Location, and Organization resources that carry patient lab results.
>
> The point is not that this is technically possible. The point is what it unlocks.
> A water authority running a FHIR server and a hospital trust running a FHIR server
> can share data without building a custom integration. One query, two datasets,
> one standard."

*(Point at the three cards: Interoperability / Model vs lab / Co-hosted)*

> "Three things PharmaShed does with that standard.
>
> First: interoperability. Every sampling site is a Location resource. Every
> prediction is an Observation resource. Any FHIR R4 consumer — a public health
> system, an epidemiology unit — can subscribe to this endpoint and filter
> by drug, by score tier, by city, in standard FHIR query syntax.
>
> Second: distinction. Category model-prediction separates our outputs from
> real lab results. Both can live on the same FHIR server, filterable by a single
> query parameter. You are never confused about whether you're looking at
> a simulation or a measurement.
>
> Third: co-hosting. PharmaShed bundles sit alongside the OneAquaHealth IG's
> own example resources. I'll show you that in a moment."

---

### Resource counts

**Point at the resource counts in the left sidebar.**

> "Left panel: resource counts. Every FHIR resource type that PharmaShed produces,
> with totals. Locations — the 105 monitoring sites, plus the OAH consortium sites.
> Observations — the model predictions. One per site per drug across five cities.
> Provenance records — one per parameter, tracking whether it's sourced or illustrative."

---

### Walk through the bundles

**Click `locations` in the sidebar. Let the JSON tree load.**

> "Click locations. [PAUSE]
>
> This is a FHIR collection bundle — 105 Location resources.
> Each one: a site ID, GPS coordinates, the city, the stream name.
> Profile: the OAH Location profile from the OneAquaHealth Implementation Guide —
> location-oah. Not a generic FHIR Location. A location that conforms to
> the consortium's environmental monitoring specification.
>
> Any system that knows the OAH IG can validate this resource against the profile
> and know exactly what it contains."

*(Collapse a few levels in the JSON tree to show structure)*

**Click `predictions-TLS` in the sidebar. Let it load.**

> "Toulouse predictions. [PAUSE]
>
> 126 Observation resources — 21 sites times 6 drugs.
> Open one. The profile is observation-with-component-oah — the OAH IG's
> environmental observation profile. The category is model-prediction,
> from our own CodeSystem — not a lab result.
>
> The components. PEC at p05, p50, and p95 — the full uncertainty band,
> not just a point estimate. RQ at p50. The priority score. LOD share —
> the fraction of draws that were below the detection limit.
>
> Every component has a unit, a code, a value. Machine-readable.
> A FHIR query for this site, this drug, filtered by score-tier — that's
> three query parameters. That's the integration path."

*(Point at the meta section in the JSON)*

> "Meta. Two tags. [PAUSE]
> oah-ig-example and illustrative-parameter.
> The second one drops the moment real sourced parameters replace illustrative ones.
> A consuming system can filter on that tag to know whether to treat a prediction
> as a prototype estimate or a production output. That distinction is machine-readable,
> not just documented in a README."

---

### Query demo panel

**Scroll down to the 'Lab vs model queries' panel.**

> "Here are the two FHIR queries that separate model predictions from lab results.
> [PAUSE]
>
> Observation?category=laboratory — that returns the consortium's lab measurements.
> Observation?category=model-prediction — that returns PharmaShed's predictions.
>
> Same server. Same endpoint. One query parameter. That's the whole point of
> category in the FHIR Observation resource — you build a heterogeneous server
> and stay able to distinguish what's in it."

---

### OAH IG Examples panel

**Scroll down to the purple-bordered OAH panel. Click 'expand'.**

> "This is the co-hosting demonstration. [PAUSE]
>
> PharmaShed loads the OneAquaHealth IG's own example resources alongside
> its own bundles. These are not our data. They come directly from the
> hl7-eu/oah repository — the canonical source of the OAH Implementation Guide —
> converted verbatim to FHIR R4 JSON and credited to the consortium.
>
> Two Location resources: Benevento monitoring sites — real coordinates,
> real Italian urban context. One Organization: ARPAC Campania, the
> regional environmental protection agency. Three Observations: benzene
> and nitrogen dioxide in Benevento air, aluminium dissolved in Almyros water.
>
> These use the same observation-with-component-oah profile as PharmaShed.
> Both sit on the same FHIR server. Category laboratory versus model-prediction
> is the query that separates them. [PAUSE]
>
> That's the OneAquaHealth vision: one FHIR server, one health ecosystem.
> Environmental, clinical, pharmaceutical. One standard. We built it."

*(Point at the resource count chips: 2 Location, 1 Organization, 3 Observation)*

> "Two Locations. One Organization. Three Observations.
> Six resources. All validating against the OAH IG profiles.
> The ValidationBadge in the sidebar confirms it."

**Point at the green validation badge in the sidebar.**

> "Validates against OneAquaHealth IG. Green. That's not decorative —
> the validation pipeline runs against the actual IG conformance rules."

*(Click assistant icon)*

---

## ASSISTANT (9:15 – 9:50)

**Click the suggested question:** *"Which Toulouse sites should I sample first for irbesartan?"*

> "The assistant runs on Groq. Open-source model, free tier.
> The constraint matters more than the model. [PAUSE]
>
> The system prompt is strict: every number in your answer must come
> from a tool call made in this conversation. Not from training data.
> Not from memory. From a live tool call."

*(Tool chip appears — point at it)*

> "It called rank_sites. Got the data back. Now it builds the answer
> from those exact results — site IDs, scores, driver sentences.
>
> A numeric guard checks every figure against the tool output before
> the response reaches you. If a number doesn't exist in the results,
> it cannot appear in the answer."

*(Point at the ranked list)*

> "Site IDs. Scores. The dominant uncertainty drivers — which parameter,
> if changed, would most shift the priority tier. In plain language.
> That's the briefing an officer reads before they leave the office."

---

## CLOSE (9:50 – 10:20)
**Back to camera.**

> "Pharmaceutical pollution in urban streams is not a new problem.
> Rodrigues found it at 91% of sites across five European cities.
> The gap isn't awareness — it's prioritisation.
>
> PharmaShed builds the decision layer that's missing.
> Monte Carlo uncertainty quantification over the untreated sewer pathway
> that every existing screening model ignores.
> Real waterway geometry. A live scenario engine.
> FHIR R4 output aligned with the OneAquaHealth Implementation Guide,
> co-hosted with consortium data on the same server.
> An assistant that can only quote numbers it can prove. [PAUSE]
>
> The parameters are illustrative. The pipeline is real.
> Replace three files — drug_parameters.csv, consumption.csv, sites.csv.
> The engine recomputes 630,000 draws, rebuilds every chart,
> regenerates every FHIR bundle. Nothing else.
>
> PharmaShed is the tool for the 91% of urban stream sites that every
> existing model predicts is fine. [PAUSE]
> They're not fine. We can prove it."

---

## BACKUP FACTS — glance here if asked anything

| Question | Answer |
|---|---|
| How many sites? | 105 — 21 per city, 5 cities |
| Which cities? | Toulouse (TLS, FR), Ghent (GNT, BE), Benevento (BNV, IT), Coimbra (CBR, PT), Oslo (OSL, NO) |
| Drugs modelled | 6: carbamazepine, atenolol, losartan, irbesartan, paracetamol, citalopram |
| Monte Carlo draws | 1,000 stored per site × drug (N_DRAWS = 1,000 per D40) |
| Score definition | Share of draws with RQ > 1. **NOT a probability. Say "priority signal under stated priors."** |
| RQ formula | PEC ÷ PNEC |
| PEC formula | (population × DDD × λ) ÷ Q |
| λ prior | log-uniform (0.002, 0.15) — untreated leakage fraction. Log scale because hotspots reach 10–15% (Fenz 2005; APUSS) while city-wide average is 0.5–3% |
| Q prior | log-uniform per stream size class; direct prior on Q (not width × depth × velocity) to avoid impossible streams |
| Why not ePiE? | ePiE routes load via WWTP outfalls; none of our 105 sites have one. ePiE predicts PEC ≈ 0 at every site. Not a bug — scope gap PharmaShed fills |
| Field data citation | Rodrigues et al. 2025, J. Hazard. Mater. 499:139946 — 102 sites, 5 cities, 91% detection, irbesartan max 31,659 ng/L (TLS) |
| λ literature basis | Fenz et al. 2005 (<3% dwf); APUSS project (0.5–3% typical); local hotspots up to 15% → log-uniform(0.002, 0.15) |
| Identifiability | λ and Q appear only as a ratio in PEC; a single grab sample cannot separate them — fundamental mathematical constraint |
| FHIR profiles used | location-oah (OAH IG), observation-with-component-oah (OAH IG) |
| FHIR category distinction | category=model-prediction (PharmaShed) vs category=laboratory (OAH IG examples and real lab data) |
| OAH examples loaded | 6 resources: 2 Location (Benevento), 1 Organization (ARPAC Campania), 3 Observation (Benzene, NO₂, aluminium dissolved) |
| OAH IG source | github.com/hl7-eu/oah — canonical HL7 EU OAH Implementation Guide |
| Illustrative tag | meta.tag: illustrative-parameter on every Observation with unverified parameters — drops when real values sourced |
| Validation badge | Green = validates against OAH IG conformance rules |
| Parameter status | Illustrative (D33) — round numbers, no citations. Sourcing pipeline built; real values slot in without code changes |
| Total draws computed | 105 sites × 6 drugs × 1,000 = 630,000 |
| LLM | Groq, open-source, tool-use loop + numeric guard — cannot quote a number not returned by a tool call |
| City field ranking (Rodrigues) | TLS > GNT > BNV > CBR ≈ OSL by total pharmaceutical load |
| Ablation sequence | WWTP-only → 0 rankings (blind spot). Pop-only → city-level ordering. Full → within-city differentiation via λ |

## NEVER SAY
- "The stream is **safe**" or "**unsafe**" → say "the model estimates concentrations for priority-setting only"
- "**Probability** of harm" → say "share of simulated draws with RQ > 1 under stated priors"
- "**Validated**" → say "consistency checks pass; full validation requires real sourced parameters"
- "**Accurate**" → say "structurally correct and ready to rerun with real parameters"
- Any number you haven't just read off the screen or this table
