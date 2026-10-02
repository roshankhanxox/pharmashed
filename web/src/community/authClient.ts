/**
 * Neon Auth client (S5). Sign-in is optional: without VITE_NEON_AUTH_URL the community features are
 * simply absent and the rest of the app behaves exactly as before.
 *
 * createAuthClient() returns only the Better Auth client (signIn, signUp, getSession, ...). The JWT our
 * API needs comes from createInternalNeonAuth(), which the library also exports and which wraps the
 * same client: its getJWTToken() reads the token Neon Auth put on the current session.
 */
import { createInternalNeonAuth } from "@neondatabase/auth";

const AUTH_URL = import.meta.env.VITE_NEON_AUTH_URL as string | undefined;

/** True when the build knows where the sign-in service is. */
export const authConfigured = Boolean(AUTH_URL);

// Typed from a real call so the default (Better Auth vanilla) API is inferred.
const make = (url: string) => createInternalNeonAuth(url);
type Neon = ReturnType<typeof make>;
let neon: Neon | null = null;

function shared(): Neon | null {
  if (!AUTH_URL) return null;
  neon ??= make(AUTH_URL);
  return neon;
}

/** The Better Auth client (signIn, signUp, signOut, getSession); null when sign-in is not configured. */
export function getAuthClient(): Neon["adapter"] | null {
  return shared()?.adapter ?? null;
}

/** A JWT for our API, or null when nobody is signed in. Neon issues them for 15 minutes. */
export async function getApiToken(): Promise<string | null> {
  const n = shared();
  return n ? await n.getJWTToken() : null;
}
