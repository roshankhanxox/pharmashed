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

import { reportPopup } from "./reportPopup";

describe("map popup", () => {
  const base = { id: "r", lat: 1, lon: 2, site_id: "TLS-01", city: "TLS", observed_at: new Date().toISOString(), checklist: { foam: "light" },
    note: "", is_sample: false, author: "Pat", mine: false };

  it("shows the author, site, answers and the unverified label", () => {
    const text = reportPopup(base).textContent ?? "";
    expect(text).toContain("Pat");
    expect(text).toContain("Near site TLS-01");
    expect(text).toContain("Foam on the water: A little");
    expect(text).toContain("Citizen report · unverified");
  });

  it("puts each question in bold, then the answer", () => {
    const bold = [...reportPopup(base).querySelectorAll("strong")].map((n) => n.textContent);
    expect(bold).toEqual(["Foam on the water: "]);
  });

  it("never turns a note into markup", () => {
    const node = reportPopup({ ...base, note: "<img src=x onerror=alert(1)><b>hi</b>", site_id: null, is_sample: true });
    expect(node.querySelector("b")).toBeNull();
    expect(node.querySelector("img")).toBeNull();
    expect(node.textContent).toContain("<b>hi</b>");
    expect(node.textContent).toContain("Not near one of our sites");
    expect(node.textContent).toContain("Sample report · unverified");
  });
});

describe("popup flag button", () => {
  const base = { id: "r", lat: 1, lon: 2, site_id: "TLS-01", city: "TLS", observed_at: new Date().toISOString(), checklist: { foam: "light" },
    note: "", is_sample: false, author: "Pat", mine: false };

  it("appears for other people's real reports and calls back with the report", () => {
    const seen: string[] = [];
    const node = reportPopup(base, (r) => seen.push(r.id));
    node.querySelector("button")!.click();
    expect(seen).toEqual(["r"]);
  });

  it("is not offered for your own report or a sample", () => {
    expect(reportPopup({ ...base, mine: true }, () => undefined).querySelector("button")).toBeNull();
    expect(reportPopup({ ...base, is_sample: true }, () => undefined).querySelector("button")).toBeNull();
  });
});
