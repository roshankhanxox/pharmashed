import { describe, expect, it } from "vitest";
import { ago, describeChecklist, hasAnswers, QUESTIONS } from "./reports";

describe("checklist helpers", () => {
  it("describes answers in question order, in plain words", () => {
    expect(describeChecklist({ foam: "light", water_colour: "cloudy", animals: ["fish", "birds"] })).toEqual([
      "Water colour: Cloudy", "Foam on the water: A little", "Animals you saw: Fish, Birds"]);
  });

  it("skips unanswered and empty questions, and keeps unknown values readable", () => {
    expect(describeChecklist({ smell: "", animals: [] })).toEqual([]);
    expect(describeChecklist({ smell: "weird" })).toEqual(["Smell: weird"]);
  });

  it("requires at least one answer", () => {
    expect(hasAnswers({})).toBe(false);
    expect(hasAnswers({ foam: "", animals: [] })).toBe(false);
    expect(hasAnswers({ foam: "none" })).toBe(true);
    expect(hasAnswers({ animals: ["fish"] })).toBe(true);
  });

  it("only one question takes several answers, like the server", () => {
    expect(QUESTIONS.filter((q) => q.multi).map((q) => q.key)).toEqual(["animals"]);
  });

  it("says how long ago, coarsely", () => {
    const now = new Date("2026-06-10T12:00:00Z");
    expect(ago("2026-06-10T08:00:00Z", now)).toBe("today");
    expect(ago("2026-06-09T08:00:00Z", now)).toBe("yesterday");
    expect(ago("2026-06-05T12:00:00Z", now)).toBe("5 days ago");
  });
});

import { distanceM, nearestSite } from "./reports";

describe("pins and sites", () => {
  it("measures a degree of longitude at the equator", () => {
    expect(distanceM({ lat: 0, lon: 0 }, { lat: 0, lon: 1 })).toBeCloseTo(111_195, -2);
  });

  it("links to the nearest site within a kilometre, else nothing", () => {
    const sites: { id: string; lonlat: [number, number] }[] = [{ id: "A", lonlat: [1, 43] }, { id: "B", lonlat: [1.1, 43] }];
    expect(nearestSite({ lat: 43, lon: 1.0005 }, sites)).toMatchObject({ id: "A" });
    expect(nearestSite({ lat: 43, lon: 1.05 }, sites)).toBeNull();
  });
});


import { photoFlagMessage } from "./reports";

describe("photo messages", () => {
  it("says nothing for a clean photo", () => {
    expect(photoFlagMessage({ id: "x", ai_ok: true, flags: {} })).toBeNull();
  });
  it("explains a flagged photo and an unchecked one", () => {
    expect(photoFlagMessage({ id: "x", ai_ok: false, flags: { people: true, plate: true } })).toMatch(/a person and a number plate/);
    expect(photoFlagMessage({ id: "x", ai_ok: false, flags: { not_a_stream: true } })).toMatch(/something other than a stream/);
    expect(photoFlagMessage({ id: "x", ai_ok: null, flags: { unchecked: true } })).toMatch(/could not check/);
  });
});
