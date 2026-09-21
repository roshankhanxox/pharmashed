# PharmaShed — Demo Script
> Second monitor only. Speak at 70% of your normal pace.
> Pause after every number — let it land. Mark [PAUSE] cues are mandatory beats.
> Target: 8–9 minutes.

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
> reach 10 to 15 percent. A log scale covers that five-order-of-magnitude spread
> without over-weighting either tail. A flat uniform prior would put too much mass
> on the high end."

*(Point at the Monte Carlo engine box)*

> "Here is the full equation. [PAUSE]
>
> PEC — predicted environmental concentration — equals population times DDD
> times lambda, divided by Q. [PAUSE]
>
> Population: the catchment size. DDD: the defined daily dose, the WHO standard
> unit for drug consumption. Lambda: the leakage fraction we just discussed.
> Q: river flow. That ratio gives concentration. Divide by PNEC — the regulatory
> no-effect threshold — and you have the risk quotient RQ.
>
> Now — why put the prior directly on Q, rather than sampling width times depth
> times velocity separately? Because sampling hydraulic variables independently
> produces impossible streams. You can easily draw a channel 10 centimetres wide
> with a flow velocity of 2 metres per second — physically nonsensical. We put
> the prior directly on Q per stream size class: small streams 5 to 100 litres
> per second, medium 20 to 500. One parameter, one draw, one coherent stream."

*(Point at the Score tier boxes — red, amber, green)*

> "For each of the 1,000 draws: draw a lambda, draw a Q, apply consumption
> uncertainty. Compute load. Divide by Q. Divide by PNEC. Count how many of those
> 1,000 draws produced RQ above 1. That fraction is the score. [PAUSE]
>
> Score above 0.5: high priority — red.
> Above 0.1: medium — amber.
> Below that: green."

*(Click the Explore tab)*

---

## EXPLORE TAB — The Map (3:20 – 3:55)
**The map opens on Toulouse. Don't click anything yet.**

> "105 sites. Five cities. The circles sit on real OpenStreetMap waterways —
> you can see the river network underneath. Every marker is downstream of
> a population centre, near overflow outfalls, where pharmaceutical load
> actually reaches the water."

*(Pan the map, hover a marker to show the tooltip)*

> "Hover over any site — you get the overall priority score, and the four
> highest-concern drugs for that site. That's the pre-field briefing.
> Before you drive anywhere. [PAUSE]
>
> Let me switch drugs."

---

## PICK A DRUG (3:55 – 4:20)

**Click `irbesartan` in the drug strip.**

> "Irbesartan — an angiotensin II receptor antagonist, front-line treatment
> for hypertension and type 2 diabetic nephropathy. Common in aging European
> populations. It has a very tight PNEC — it's an endocrine-active compound
> with documented effects at low concentrations. Watch the map." [PAUSE]

*(Let it re-render)*

> "More red. Different distribution than the default drug. The PNEC is what
> determines whether a given concentration is a problem — and irbesartan's
> tolerance is one of the tightest in our set. Same catchment, same population,
> same leakage — completely different risk profile."

---

## CLICK A RED SITE (4:20 – 5:30)

**Click the highest-scoring red marker visible.**

> "Let me open the highest-priority site." [PAUSE]

*(Site inspector opens on the right)*

**Point at the score number.**

> "Sampling priority score: [read it]. [PAUSE]
> That means in [score × 100]% of our 1,000 simulated draws, the predicted
> concentration of irbesartan at this site exceeded the regulatory no-effect
> threshold. This is not a probability of harm. It is a priority signal under
> the stated prior assumptions. The distinction matters — always say priority
> signal, not risk probability."

**Point at the band chart rows.**

> "This chart shows all six drugs at once. Each row is one drug.
> The horizontal bar is the uncertainty band — 5th percentile on the left,
> 95th on the right, median dot in the centre.
> That's the spread of predicted concentrations across 1,000 draws. [PAUSE]
>
> The x-axis is predicted concentration in nanograms per litre.
> The vertical dashed line is the PNEC — the regulatory no-effect threshold
> for that specific drug. Everything to the right of that line represents
> draws where the model estimated harm. When the entire bar sits past the
> line — like it does here — the score is close to 1."

**Click on the irbesartan row to expand it.**

*(Point at the histogram)*

> "Expand it. [PAUSE]
>
> This is the raw simulation output. Every bar is a bucket of log-concentration
> draws. The coloured region is the portion where RQ exceeded 1.
> Count those bars, divide by total — that's the number you just read off the screen.
> There is no black box. You are looking at the simulation directly."

**Switch to `citalopram` in the drug strip.**

> "Same site. Same population. Same leakage prior. Switch to citalopram —
> an SSRI antidepressant with a higher PNEC, a more forgiving threshold.
> The bar sits in a similar position but fewer draws cross the line. Lower score.
> Same site, different drug, completely different answer. [PAUSE]
> That's why you filter by drug before you pick your eight sites."

*(Click Scenarios tab)*

---

## SCENARIOS TAB (5:30 – 6:15)

*(Make sure a site is already selected — if not, go back to Explore, pick one, return)*

**Click `Drought` preset.**

> "Q — river flow — sits in the denominator of the concentration equation.
> Less water, same pharmaceutical load — higher concentration. [PAUSE]
>
> Drought scenario: flow drops to 20% of baseline. A southern European summer."

*(Point at score shifting)*

> "Score jumps. Same site, same drug, same population — just a drier river.
> This is what a climate adaptation officer needs before a heat event,
> not after one."

**Click `Sewer repair`.**

> "Flip direction. A sewer rehabilitation project cuts untreated discharge
> by half — lambda drops by 50%. Score falls. [PAUSE]
>
> That number on screen is what an infrastructure team takes into a budget
> meeting. If we invest in this repair, the priority score drops from high
> to medium at this site. Is that investment justified? Now they can model it."

**Drag the λ slider.**

> "And you can explore it continuously — every slider position reruns the
> score live over the stored draw set. No server call. Float32 arithmetic
> in the browser over 630,000 precomputed draws."

*(Click Methodology tab)*

---

## METHODOLOGY TAB (6:15 – 7:10)

**Scroll through it slowly as you talk.**

> "The full model specification is here — not in a supplementary PDF, in the product.
> Every stage, every prior, every assumption. Reviewers can read the pipeline
> while they use the output."

**Scroll to the priors table.**

> "The priors table. Every parameter — its distribution, its source, its status.
> The ones marked illustrative are placeholder values: deliberately round numbers,
> within a plausible order of magnitude, with no citation attached. That's D33
> in our design log — the deliberate choice to badge uncertainty rather than
> present unsourced numbers as data. [PAUSE]
>
> The sourcing pipeline is already built. Replace drug_parameters.csv and
> consumption.csv — three files total — and the engine recomputes 630,000 draws,
> rebuilds every chart, regenerates every FHIR bundle. Nothing else changes."

**Scroll to the identifiability callout.**

> "This is the intellectually honest part. Lambda and Q appear only as a ratio
> in the PEC equation. A single grab sample cannot tell you whether a high
> observed concentration came from heavy sewer leakage or a low-flow day.
> That is a fundamental identifiability constraint — you cannot separate the
> two parameters from one measurement. [PAUSE]
>
> PharmaShed doesn't paper over it with a point estimate. We propagate the
> prior uncertainty through every draw and show you the full distribution.
> A tool that gives you a single number here is either using a hidden assumption
> or ignoring the constraint entirely. We think that's the wrong trade-off
> when you're deciding where to deploy a sampling team."

**Scroll to ablation comparison.**

> "The ablation. Three model variants side by side. [PAUSE]
>
> WWTP-only — that's the ePiE equivalent. Every site scores zero because
> none of the 105 sites has a WWTP on stream. Not a bug — that's the
> scope gap we're filling, made visible.
>
> Population-only — adds consumption and population density, no leakage term.
> Sites near dense catchments start appearing.
>
> Full model — adds lambda, the untreated pathway. Rankings sharpen.
>
> The check is whether site rankings stay stable as you add components.
> If they hold, each addition carries genuine signal. If they collapse,
> the model is fragile. Ours holds."

*(Click Consistency tab)*

---

## CONSISTENCY TAB (7:10 – 7:45)

**Scroll through the five checks.**

> "Five pre-registered validation checks. [PAUSE]
>
> Pre-registered means the predictions were frozen before any comparison
> was run against the Rodrigues field data. No tuning after the fact.
> That's the scientific discipline — you declare what you expect to see
> before you look.
>
> C1: does the model predict the right fraction of sites above the detection limit?
> C2: does our city rank order match the observed total load ranking?
>    — the field study found Toulouse, then Ghent, then Benevento, then
>    Coimbra and Oslo roughly tied. Does our model recover that ordering?
> C3: are our PEC concentration bands in the right order of magnitude?
> C4: do relative drug rankings hold across cities?
> C5: do the ablation variant rankings stay stable as components are added?
>
> These checks aren't passing because the model is calibrated. They're passing
> because the validation pipeline is structurally correct and ready to run again
> the moment real sourced parameters replace the illustrative ones."

*(Click FHIR tab)*

---

## FHIR TAB (7:45 – 8:25)

**Look at the bundle list on the left.**

> "The IEEE OneAquaHealth track requires FHIR R4 interoperability.
> Every data object in PharmaShed has a FHIR representation,
> and they align with the OneAquaHealth Implementation Guide profiles."

**Click `locations` in the sidebar.**

> "Every sampling site is a FHIR Location resource using the OAH Location profile —
> GPS coordinates, site ID, city. Any FHIR-compliant system ingests this
> without a custom integration layer."

**Click `predictions-TLS` in the sidebar.**

> "This is the Toulouse prediction bundle.
> 126 FHIR Observation resources — 21 sites times 6 drugs. [PAUSE]
> Each Observation carries the PEC band at p05, p50, and p95;
> the RQ at p50; the priority score; and the LOD share.
> The category is model-prediction, from the OAH CodeSystem.
> Provenance keys link each record back to its parameter sources
> and flag whether they are sourced or illustrative — machine-readably.
>
> A water authority, an epidemiology unit, a hospital trust — any FHIR R4
> consumer can subscribe to this endpoint and immediately filter by drug,
> by score tier, by city. That's not a demo feature. That is the integration path."

**Click the OAH examples panel.**

> "And we loaded the OneAquaHealth IG's own example resources alongside ours.
> Benevento air-quality sites. Almyros water chemistry observations.
> PharmaShed bundles and consortium data coexist in the same FHIR server,
> distinguishable by category and tag. That's the co-hosting model D38
> describes."

*(Click assistant icon)*

---

## ASSISTANT (8:25 – 9:00)

**Click the suggested question:** *"Which Toulouse sites should I sample first for irbesartan?"*

> "The assistant runs on Groq. Open-source LLM, free tier.
> But the constraint matters more than the model. [PAUSE]
>
> The system prompt is strict: every number in your answer must come
> from a tool call made in this conversation. No hallucinated scores."

*(Tool chip appears — point at it)*

> "It called rank_sites first. Got the live data back.
> Now it's building the answer from those exact results —
> site IDs, scores, the driver sentence for each.
> A numeric guard checks every figure against the tool output before
> the response reaches you. If the number doesn't exist in the results,
> it doesn't appear in the answer."

*(Point at the ranked list in the response)*

> "A ranked list. Sites. Scores. The dominant uncertainty drivers.
> In plain language.
> That's the briefing an officer reads before they leave the office."

---

## CLOSE (9:00 – 9:30)
**Back to camera.**

> "Pharmaceutical pollution in urban streams is not a new problem.
> The Rodrigues study found it at 91% of sites. The gap isn't awareness —
> it's prioritisation. A hundred sites, eight visits, no principled way to choose.
>
> PharmaShed builds that decision layer. Monte Carlo uncertainty quantification
> over the untreated sewer pathway that every existing screening model ignores.
> Real waterway geometry. A live scenario engine. FHIR R4 output aligned with
> the OneAquaHealth IG. And an assistant that can only quote numbers it can prove.
>
> The parameters are illustrative. The pipeline is real.
> Replace three files — get the priority scores for any city you want.
> 630,000 draws. Every chart. Every FHIR bundle. Nothing else.
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
| λ prior | log-uniform (0.002, 0.15) — untreated leakage fraction. Log scale because hotspots reach 10–15% (Fenz 2005; APUSS project) while city-wide average is 0.5–3% |
| Q prior | log-uniform per stream size class; direct prior on Q (not width × depth × velocity) to avoid impossible streams |
| Why not ePiE? | ePiE routes load via WWTP outfalls; none of our 105 sites have one. ePiE predicts PEC ≈ 0 at every site. That's not a bug — it's the scope gap PharmaShed fills |
| Field data citation | Rodrigues et al. 2025, J. Hazard. Mater. 499:139946 — 102 sites, 5 cities, 91% detection, irbesartan max 31,659 ng/L (TLS) |
| λ literature basis | Fenz et al. 2005 (<3% dwf); APUSS project (0.5–3% typical); local hotspots up to 15% → log-uniform(0.002, 0.15) |
| Identifiability | λ and Q appear only as a ratio in PEC; a single grab sample cannot separate them — fundamental constraint, not a gap |
| FHIR version | R4 — Location (OAH profile), Observation (observation-with-component-oah), category model-prediction from OAH CodeSystem |
| Parameter status | Illustrative (D33) — round numbers, no citations. Sourcing pipeline built; real values slot in without code changes |
| Total draws computed | 105 sites × 6 drugs × 1,000 = 630,000 |
| LLM | Groq, open-source, tool-use loop + numeric guard — cannot quote a number not returned by a tool call |
| City field ranking (Rodrigues) | TLS > GNT > BNV > CBR ≈ OSL by total pharmaceutical load |

## NEVER SAY
- "The stream is **safe**" or "**unsafe**" → say "the model estimates concentrations for priority-setting only"
- "**Probability** of harm" → say "share of simulated draws with RQ > 1 under stated priors"
- "**Validated**" → say "consistency checks pass; full validation requires real sourced parameters"
- Any number you haven't just read off the screen or this table
