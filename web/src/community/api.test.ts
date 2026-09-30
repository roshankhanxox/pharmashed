import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./authClient", () => ({ getApiToken: vi.fn(async () => "tok-123"), authConfigured: true, getAuthClient: () => null }));
vi.mock("../data/loaders", () => ({ apiBase: () => "https://api.test/api" }));

import { ApiError, apiFetch, errorMessage } from "./api";
import { getApiToken } from "./authClient";

afterEach(() => vi.restoreAllMocks());

describe("errorMessage", () => {
  it("uses a string detail as is", () => {
    expect(errorMessage({ detail: "That nickname is taken. Please pick another." }, "x")).toBe("That nickname is taken. Please pick another.");
  });

  it("uses the first validation message and drops pydantic's 'Value error,' prefix", () => {
    expect(errorMessage({ detail: [{ msg: "Value error, Use 3 to 20 characters." }] }, "x")).toBe("Use 3 to 20 characters.");
  });

  it("falls back when the body has nothing usable", () => {
    expect(errorMessage(null, "fallback")).toBe("fallback");
    expect(errorMessage({ detail: [] }, "fallback")).toBe("fallback");
    expect(errorMessage({}, "fallback")).toBe("fallback");
  });
});

describe("apiFetch", () => {
  const respond = (status: number, body: unknown) =>
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(body), { status }));

  it("sends the bearer token only when asked", async () => {
    const spy = respond(200, { ok: true });
    await apiFetch("/me", { auth: true });
    expect(spy).toHaveBeenCalledWith("https://api.test/api/me", expect.anything());
    const headers = spy.mock.calls[0][1]!.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok-123");

    await apiFetch("/community/status");
    expect((spy.mock.calls[1][1]!.headers as Headers).has("Authorization")).toBe(false);
  });

  it("does not call the server when auth is required but nobody is signed in", async () => {
    vi.mocked(getApiToken).mockResolvedValueOnce(null);
    const spy = respond(200, {});
    await expect(apiFetch("/me", { auth: true })).rejects.toMatchObject({ status: 401 });
    expect(spy).not.toHaveBeenCalled();
  });

  it("turns an error response into an ApiError with a readable message", async () => {
    respond(409, { detail: "That nickname is taken. Please pick another." });
    await expect(apiFetch("/me/profile", { method: "PUT", body: "{}" })).rejects.toEqual(
      expect.objectContaining({ status: 409, message: "That nickname is taken. Please pick another." }),
    );
  });

  it("sets a JSON content type when there is a body", async () => {
    const spy = respond(200, {});
    await apiFetch("/me/profile", { method: "PUT", body: "{}" });
    expect((spy.mock.calls[0][1]!.headers as Headers).get("Content-Type")).toBe("application/json");
  });

  it("explains a network failure instead of throwing a raw error", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const err = (await apiFetch("/me").catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(err.message).toMatch(/could not reach the server/i);
  });
});
