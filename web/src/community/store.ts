/**
 * Community state (S5): whether the feature is available, who is signed in, and their profile.
 * Available only when the build has an auth URL *and* the server reports a database and sign-in.
 */
import { create } from "zustand";
import { apiFetch, ApiError } from "./api";
import { authConfigured, getAuthClient } from "./authClient";

export interface Profile {
  nickname: string;
  show_on_leaderboard: boolean;
  home_city: string | null;
  created_at: string;
}

interface MeResponse {
  user: { name: string | null };
  profile: Profile | null;
  is_admin: boolean;
}

export interface ProfileInput {
  nickname: string;
  show_on_leaderboard: boolean;
  home_city: string | null;
}

interface CommunityState {
  /** "unknown" until checked; "unavailable" hides every community control. */
  availability: "unknown" | "unavailable" | "ready";
  /** The server can store photos (the bucket is configured). */
  photosEnabled: boolean;
  signedIn: boolean;
  userName: string | null;
  profile: Profile | null;
  isAdmin: boolean;
  busy: boolean;
  error: string | null;
  authDialog: "closed" | "signin" | "signup";
  nicknameDialogOpen: boolean;
  privacyOpen: boolean;
  deleteDialogOpen: boolean;

  init: () => Promise<void>;
  refresh: () => Promise<void>;
  openAuthDialog: (mode: "signin" | "signup") => void;
  closeAuthDialog: () => void;
  openNicknameDialog: () => void;
  closeNicknameDialog: () => void;
  openPrivacy: () => void;
  closePrivacy: () => void;
  openDeleteDialog: () => void;
  closeDeleteDialog: () => void;
  /** Deletes the account and everything held about it, then signs out. */
  deleteAccount: () => Promise<boolean>;
  signInEmail: (email: string, password: string) => Promise<boolean>;
  signUpEmail: (name: string, email: string, password: string) => Promise<boolean>;
  signInGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  saveProfile: (input: ProfileInput) => Promise<boolean>;
}

const messageOf = (e: unknown, fallback: string): string =>
  e instanceof ApiError ? e.message : e instanceof Error && e.message ? e.message : fallback;

export const useCommunity = create<CommunityState>((set, get) => ({
  availability: "unknown",
  photosEnabled: false,
  signedIn: false,
  userName: null,
  profile: null,
  isAdmin: false,
  busy: false,
  error: null,
  authDialog: "closed",
  nicknameDialogOpen: false,
  privacyOpen: false,
  deleteDialogOpen: false,

  init: async () => {
    if (!authConfigured) {
      set({ availability: "unavailable" });
      return;
    }
    try {
      const status = await apiFetch<{ enabled: boolean; photos?: boolean }>("/community/status");
      if (!status.enabled) {
        set({ availability: "unavailable" });
        return;
      }
      set({ availability: "ready", photosEnabled: status.photos === true });
      await get().refresh();
    } catch {
      // The server is down or has no community support: leave the rest of the app untouched.
      set({ availability: "unavailable" });
    }
  },

  /** Re-reads the session and, if signed in, the profile. Opens the nickname dialog if none exists. */
  refresh: async () => {
    const client = getAuthClient();
    if (!client) return;
    const session = await client.getSession();
    if (!session?.data?.user) {
      set({ signedIn: false, userName: null, profile: null, isAdmin: false });
      return;
    }
    try {
      const me = await apiFetch<MeResponse>("/me", { auth: true });
      set({
        signedIn: true,
        userName: me.user.name,
        profile: me.profile,
        isAdmin: me.is_admin,
        nicknameDialogOpen: me.profile === null,
        error: null,
      });
    } catch (e) {
      set({ signedIn: true, error: messageOf(e, "Could not load your profile.") });
    }
  },

  openAuthDialog: (mode) => set({ authDialog: mode, error: null }),
  closeAuthDialog: () => set({ authDialog: "closed", error: null }),
  openNicknameDialog: () => set({ nicknameDialogOpen: true, error: null }),
  closeNicknameDialog: () => set({ nicknameDialogOpen: false, error: null }),
  openPrivacy: () => set({ privacyOpen: true }),
  closePrivacy: () => set({ privacyOpen: false }),
  openDeleteDialog: () => set({ deleteDialogOpen: true, error: null }),
  closeDeleteDialog: () => set({ deleteDialogOpen: false, error: null }),

  deleteAccount: async () => {
    set({ busy: true, error: null });
    try {
      await apiFetch<unknown>("/me", { method: "DELETE", auth: true });
    } catch (e) {
      set({ busy: false, error: messageOf(e, "Could not delete your account. Please try again.") });
      return false;
    }
    // The account is gone on the server; ending the local session may fail because the session no longer exists.
    try {
      await getAuthClient()?.signOut();
    } catch {
      /* nothing left to sign out of */
    }
    set({ busy: false, deleteDialogOpen: false, signedIn: false, userName: null, profile: null, isAdmin: false, nicknameDialogOpen: false });
    return true;
  },

  signInEmail: async (email, password) => {
    const client = getAuthClient();
    if (!client) return false;
    set({ busy: true, error: null });
    try {
      const { error } = await client.signIn.email({ email, password });
      if (error) {
        set({ busy: false, error: error.message ?? "Sign-in failed. Check your email and password." });
        return false;
      }
      // Keep the dialog open (with its "One moment" state) until the profile has loaded: the first
      // sign-in can take a few seconds while Neon wakes up, and a closed dialog would look frozen.
      await get().refresh();
      set({ busy: false, authDialog: "closed" });
      return true;
    } catch (e) {
      set({ busy: false, error: messageOf(e, "Sign-in failed. Please try again.") });
      return false;
    }
  },

  signUpEmail: async (name, email, password) => {
    const client = getAuthClient();
    if (!client) return false;
    set({ busy: true, error: null });
    try {
      const { error } = await client.signUp.email({ name, email, password });
      if (error) {
        set({ busy: false, error: error.message ?? "Could not create the account." });
        return false;
      }
      await get().refresh();
      set({ busy: false, authDialog: "closed" });
      return true;
    } catch (e) {
      set({ busy: false, error: messageOf(e, "Could not create the account. Please try again.") });
      return false;
    }
  },

  signInGoogle: async () => {
    const client = getAuthClient();
    if (!client) return;
    set({ error: null });
    try {
      // Redirects to Google and back; the page reloads and init() picks up the session.
      await client.signIn.social({ provider: "google", callbackURL: window.location.origin });
    } catch (e) {
      set({ error: messageOf(e, "Google sign-in failed. Please try again.") });
    }
  },

  signOut: async () => {
    await getAuthClient()?.signOut();
    set({ signedIn: false, userName: null, profile: null, isAdmin: false, nicknameDialogOpen: false });
  },

  saveProfile: async (input) => {
    set({ busy: true, error: null });
    try {
      const profile = await apiFetch<Profile>("/me/profile", {
        method: "PUT",
        auth: true,
        body: JSON.stringify(input),
      });
      set({ busy: false, profile, nicknameDialogOpen: false });
      return true;
    } catch (e) {
      set({ busy: false, error: messageOf(e, "Could not save your profile.") });
      return false;
    }
  },
}));
