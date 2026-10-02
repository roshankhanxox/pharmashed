import { beforeEach, describe, expect, it, vi } from "vitest";

const client = {
  getSession: vi.fn(),
  signIn: { email: vi.fn(), social: vi.fn() },
  signUp: { email: vi.fn() },
  signOut: vi.fn(),
};
const apiFetch = vi.fn();

async function load(configured: boolean) {
  vi.resetModules();
  vi.doMock("./authClient", () => ({ authConfigured: configured, getAuthClient: () => (configured ? client : null), getApiToken: async () => "t" }));
  vi.doMock("./api", () => ({
    apiFetch,
    ApiError: class ApiError extends Error {
      status: number;
      constructor(status: number, message: string) { super(message); this.status = status; }
    },
  }));
  return (await import("./store")).useCommunity;
}

const profile = { nickname: "RiverPat", show_on_leaderboard: true, home_city: "TLS", created_at: "2026-09-29T00:00:00Z" };
const signedIn = () => client.getSession.mockResolvedValue({ data: { user: { id: "u1" }, session: { token: "jwt" } } });

beforeEach(() => {
  apiFetch.mockReset();
  client.getSession.mockReset();
  client.signIn.email.mockReset();
  client.signUp.email.mockReset();
  client.signOut.mockReset();
});

describe("availability", () => {
  it("is unavailable, and never calls the server, when the build has no auth URL", async () => {
    const store = await load(false);
    await store.getState().init();
    expect(store.getState().availability).toBe("unavailable");
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("is unavailable when the server says community features are off", async () => {
    apiFetch.mockResolvedValue({ enabled: false });
    const store = await load(true);
    await store.getState().init();
    expect(store.getState().availability).toBe("unavailable");
  });

  it("is unavailable, quietly, when the server cannot be reached", async () => {
    apiFetch.mockRejectedValue(new Error("down"));
    const store = await load(true);
    await store.getState().init();
    expect(store.getState().availability).toBe("unavailable");
  });

  it("is ready and signed out when enabled and there is no session", async () => {
    apiFetch.mockResolvedValue({ enabled: true });
    client.getSession.mockResolvedValue({ data: null });
    const store = await load(true);
    await store.getState().init();
    expect(store.getState()).toMatchObject({ availability: "ready", signedIn: false, profile: null });
  });
});

describe("session and profile", () => {
  it("loads the profile for a signed-in user and does not nag when they have one", async () => {
    apiFetch.mockResolvedValueOnce({ enabled: true }).mockResolvedValueOnce({ user: { name: "Pat" }, profile, is_admin: false });
    signedIn();
    const store = await load(true);
    await store.getState().init();
    expect(store.getState()).toMatchObject({ signedIn: true, userName: "Pat", profile, nicknameDialogOpen: false });
  });

  it("opens the nickname dialog for a signed-in user who has none yet", async () => {
    apiFetch.mockResolvedValueOnce({ enabled: true }).mockResolvedValueOnce({ user: { name: "Pat" }, profile: null, is_admin: false });
    signedIn();
    const store = await load(true);
    await store.getState().init();
    expect(store.getState().nicknameDialogOpen).toBe(true);
  });

  it("keeps the user signed in and shows a message if the profile call fails", async () => {
    apiFetch.mockResolvedValueOnce({ enabled: true }).mockRejectedValueOnce(new Error("boom"));
    signedIn();
    const store = await load(true);
    await store.getState().init();
    expect(store.getState().signedIn).toBe(true);
    expect(store.getState().error).toBe("boom");
  });

  it("saves a profile through the API and closes the dialog", async () => {
    apiFetch.mockResolvedValue(profile);
    const store = await load(true);
    store.setState({ nicknameDialogOpen: true });
    const ok = await store.getState().saveProfile({ nickname: "RiverPat", show_on_leaderboard: true, home_city: "TLS" });
    expect(ok).toBe(true);
    expect(apiFetch).toHaveBeenCalledWith("/me/profile", expect.objectContaining({ method: "PUT", auth: true }));
    expect(store.getState()).toMatchObject({ profile, nicknameDialogOpen: false, busy: false });
  });

  it("keeps the dialog open and shows the server's message when the nickname is taken", async () => {
    apiFetch.mockRejectedValue(new Error("That nickname is taken. Please pick another."));
    const store = await load(true);
    store.setState({ nicknameDialogOpen: true });
    expect(await store.getState().saveProfile({ nickname: "x", show_on_leaderboard: true, home_city: null })).toBe(false);
    expect(store.getState()).toMatchObject({ nicknameDialogOpen: true, error: "That nickname is taken. Please pick another.", busy: false });
  });
});

describe("signing in and out", () => {
  it("shows the service's message when the password is wrong", async () => {
    client.signIn.email.mockResolvedValue({ error: { message: "Invalid email or password" } });
    const store = await load(true);
    expect(await store.getState().signInEmail("a@b.co", "nope")).toBe(false);
    expect(store.getState()).toMatchObject({ error: "Invalid email or password", busy: false });
  });

  it("closes the dialog and refreshes after a successful sign-in", async () => {
    client.signIn.email.mockResolvedValue({ data: {}, error: null });
    apiFetch.mockResolvedValue({ user: { name: "Pat" }, profile, is_admin: false });
    signedIn();
    const store = await load(true);
    store.setState({ authDialog: "signin" });
    expect(await store.getState().signInEmail("a@b.co", "pw")).toBe(true);
    expect(store.getState()).toMatchObject({ authDialog: "closed", signedIn: true, profile });
  });

  it("keeps the sign-in dialog open, busy, until the profile has loaded", async () => {
    client.signIn.email.mockResolvedValue({ data: {}, error: null });
    let release: (v: unknown) => void = () => {};
    apiFetch.mockReturnValue(new Promise((resolve) => { release = resolve; }));   // /me is slow (Neon waking up)
    signedIn();
    const store = await load(true);
    store.setState({ authDialog: "signin" });
    const pending = store.getState().signInEmail("a@b.co", "pw");
    await new Promise((r) => setTimeout(r, 10));
    expect(store.getState()).toMatchObject({ authDialog: "signin", busy: true });   // still showing "One moment"
    release({ user: { name: "Pat" }, profile, is_admin: false });
    await pending;
    expect(store.getState()).toMatchObject({ authDialog: "closed", busy: false, signedIn: true });
  });

  it("creates an account with the name, email and password", async () => {
    client.signUp.email.mockResolvedValue({ data: {}, error: null });
    apiFetch.mockResolvedValue({ user: { name: "Pat" }, profile: null, is_admin: false });
    signedIn();
    const store = await load(true);
    await store.getState().signUpEmail("Pat", "a@b.co", "longenough");
    expect(client.signUp.email).toHaveBeenCalledWith({ name: "Pat", email: "a@b.co", password: "longenough" });
  });

  it("clears everything on sign-out", async () => {
    const store = await load(true);
    store.setState({ signedIn: true, userName: "Pat", profile, isAdmin: true });
    await store.getState().signOut();
    expect(client.signOut).toHaveBeenCalled();
    expect(store.getState()).toMatchObject({ signedIn: false, userName: null, profile: null, isAdmin: false });
  });
});
