/** Calls to our API that need the signed-in user's token, and readable error messages from it. */
import { apiBase } from "../data/loaders";
import { getApiToken } from "./authClient";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** Turns FastAPI's error body into one sentence: a string detail, or the first validation message. */
export function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    // pydantic prefixes messages raised by our validators with "Value error, "
    if (first?.msg) return first.msg.replace(/^Value error,\s*/i, "");
  }
  return fallback;
}

/** fetch against the API. With `auth`, sends the Neon token as a Bearer header. Throws ApiError. */
export async function apiFetch<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = false, headers, ...rest } = init;
  const merged = new Headers(headers);
  if (rest.body && !(rest.body instanceof FormData) && !merged.has("Content-Type")) merged.set("Content-Type", "application/json");
  if (auth) {
    const token = await getApiToken();
    if (!token) throw new ApiError(401, "You are not signed in.");
    merged.set("Authorization", `Bearer ${token}`);
  }

  let res: Response;
  try {
    res = await fetch(`${apiBase()}${path}`, { ...rest, headers: merged });
  } catch {
    throw new ApiError(0, "Could not reach the server. Check your connection and try again.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, errorMessage(body, `Request failed (${res.status}).`));
  return body as T;
}
