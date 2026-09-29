/**
 * What the FHIR tab's validation badge says. The badge must never claim a pass that was not
 * measured: the fixture/index data carries status "unknown" until the HL7 validator has run.
 */

export interface ValidationInfo {
  status?: string;
  errors?: number;
  warnings?: number;
  validator_version?: string | null;
  ran_at?: string | null;
}

export interface BadgeState {
  tone: "ok" | "warn" | "neutral";
  text: string;
}

/** Turns the validation record into badge text. Green only for a recorded pass. */
export function validationBadge(v?: ValidationInfo): BadgeState {
  const errors = v?.errors ?? 0;
  if (v?.status === "fail" || errors > 0) {
    return { tone: "warn", text: `⚠ ${errors} validation error${errors === 1 ? "" : "s"}` };
  }
  if (v?.status === "pass" && v.ran_at) {
    const version = v.validator_version ? ` ${v.validator_version}` : "";
    const warnings = v.warnings ?? 0;
    const notes = warnings > 0 ? `, ${warnings.toLocaleString("en-US")} warning${warnings === 1 ? "" : "s"}` : "";
    return {
      tone: "ok",
      text: `✓ Passed the HL7 validator${version} against the OneAquaHealth IG (${v.ran_at.slice(0, 10)}): 0 errors${notes}`,
    };
  }
  return { tone: "neutral", text: "Not yet validated: the HL7 validator has not been run on these bundles." };
}
