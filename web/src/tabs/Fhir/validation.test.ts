import { describe, expect, it } from "vitest";
import { validationBadge } from "./validation";

describe("validationBadge", () => {
  it("does not claim a pass when the validator has never run", () => {
    const never = { status: "unknown", errors: 0, warnings: 0, validator_version: null, ran_at: null };
    expect(validationBadge(never).tone).toBe("neutral");
    expect(validationBadge(never).text).not.toMatch(/✓|passed|validates/i);
    expect(validationBadge(undefined).tone).toBe("neutral");
  });

  it("does not trust status=pass without a recorded run", () => {
    expect(validationBadge({ status: "pass", errors: 0, ran_at: null }).tone).toBe("neutral");
  });

  it("goes green only for a recorded pass, with version and date", () => {
    const b = validationBadge({ status: "pass", errors: 0, validator_version: "6.3.0", ran_at: "2026-09-30T10:00:00Z" });
    expect(b.tone).toBe("ok");
    expect(b.text).toContain("6.3.0");
    expect(b.text).toContain("2026-09-30");
  });

  it("reports errors, singular and plural", () => {
    expect(validationBadge({ status: "fail", errors: 1 }).text).toBe("⚠ 1 validation error");
    expect(validationBadge({ status: "fail", errors: 3 }).text).toBe("⚠ 3 validation errors");
  });
});
