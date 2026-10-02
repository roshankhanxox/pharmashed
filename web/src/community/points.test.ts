import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
vi.mock("./api", () => ({ apiFetch }));

const { fetchBoard, signed, STATUS_LABEL, HOW_POINTS_WORK } = await import("./points");

beforeEach(() => apiFetch.mockReset().mockResolvedValue({}));

describe("points helpers", () => {
  it("signs numbers", () => {
    expect([signed(10), signed(0), signed(-5)]).toEqual(["+10", "0", "-5"]);
  });

  it("asks for the right board, sending the token only when signed in", async () => {
    await fetchBoard("week", "OSL", true);
    expect(apiFetch).toHaveBeenLastCalledWith("/leaderboard?scope=week&city=OSL", { auth: true });
    await fetchBoard("all", null, false);
    expect(apiFetch).toHaveBeenLastCalledWith("/leaderboard?scope=all", { auth: false });
  });

  it("has a plain label for every review status and lists the caps in the rules", () => {
    expect(Object.keys(STATUS_LABEL).sort()).toEqual(["approved", "hidden", "pending"]);
    expect(HOW_POINTS_WORK.join(" ")).toMatch(/3 rewarded reports a day/);
  });
});
