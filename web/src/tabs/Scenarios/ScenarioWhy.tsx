/**
 * "Why does it change?" card for the What-if tab. Explains the mechanism of the chosen
 * change, what happened at this site and medicine, and why results differ between places.
 * Citizen wording is plain; expert wording uses the model's terms.
 */
import { DEMO_NOTICE, SCORE_CAVEAT } from "../../data/copy";
import {
  crossingDetail, effectSentences, outcomeSentence, whyDiffers,
  type Multipliers, type Outcome,
} from "../../data/scenarioWhy";

interface ScenarioWhyProps {
  citizen: boolean;
  multipliers: Multipliers;
  baseline: Outcome;
  scenario: Outcome;
}

export function ScenarioWhy({ citizen, multipliers, baseline, scenario }: ScenarioWhyProps) {
  const effects = effectSentences(multipliers, citizen);
  const changed = effects.length > 0;

  return (
    <div className="rounded-xl p-5 flex flex-col gap-4" style={{ background: "var(--c-surface)", border: "1px solid var(--c-border)" }}>
      <h3 className="font-semibold" style={{ fontSize: "1.0625rem" }}>Why does it change?</h3>

      {changed ? (
        <div className="flex flex-col gap-3 text-sm leading-relaxed" style={{ color: "var(--c-muted)" }}>
          <div>
            <div className="font-medium mb-1" style={{ color: "var(--c-text)" }}>
              {citizen ? "What this change does" : "Effect of the change"}
            </div>
            <ul className="list-disc pl-5 flex flex-col gap-1">
              {effects.map((e) => <li key={e}>{e}</li>)}
            </ul>
          </div>
          <div>
            <div className="font-medium mb-1" style={{ color: "var(--c-text)" }}>
              {citizen ? "What happened here" : "Result at this site and drug"}
            </div>
            <p>{outcomeSentence(baseline, scenario, citizen)}</p>
            {!citizen && (
              <p className="mt-1" style={{ color: "var(--c-muted2)" }}>{crossingDetail(baseline, scenario, multipliers)}</p>
            )}
          </div>
        </div>
      ) : (
        <p className="text-sm leading-relaxed" style={{ color: "var(--c-muted)" }}>
          {citizen
            ? "Pick a change on the left. This card will explain what it does to the stream and why the ranking moves, or doesn't."
            : "Choose a preset or move a slider. Each change rescales every stored RQ draw by λ × C / Q, and the score is the share that ends above 1."}
        </p>
      )}

      <div className="text-sm leading-relaxed" style={{ color: "var(--c-muted)" }}>
        <div className="font-medium mb-1" style={{ color: "var(--c-text)" }}>
          {citizen ? "Why results differ from place to place" : "Why the same change differs between sites"}
        </div>
        <p>{whyDiffers(citizen)}</p>
      </div>

      {!citizen && (
        <p className="text-xs leading-relaxed" style={{ color: "var(--c-muted2)" }}>
          Scenario scores are exact rescalings of the stored draws because every site has w = 0 (all load arrives by the untreated pathway).
        </p>
      )}
      {citizen && (
        <p className="text-sm leading-relaxed" style={{ color: "var(--c-muted2)" }}>{SCORE_CAVEAT} {DEMO_NOTICE}</p>
      )}
    </div>
  );
}
