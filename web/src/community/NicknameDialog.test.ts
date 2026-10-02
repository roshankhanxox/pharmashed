import { describe, expect, it } from "vitest";
import { nicknameProblem } from "./NicknameDialog";

describe("nicknameProblem (instant feedback; the server enforces the full rules)", () => {
  it("accepts good nicknames", () => {
    for (const n of ["Pat", "river-watcher", "Stream_Fan_99", "  Padded  "]) expect(nicknameProblem(n)).toBeNull();
  });

  it("explains what is wrong", () => {
    expect(nicknameProblem("ab")).toMatch(/3 to 20/);
    expect(nicknameProblem("x".repeat(21))).toMatch(/3 to 20/);
    expect(nicknameProblem("has space")).toMatch(/only letters/);
    expect(nicknameProblem("a@b.com")).toMatch(/only letters/);
    expect(nicknameProblem("12345")).toMatch(/at least one letter/);
  });
});
