/**
 * Fetch build artifacts from either /api (dev) or /data (static demo).
 * VITE_DATA_BASE controls the source; defaults to /api.
 * In API mode, routes are /api/results, /api/sites, etc. (no .json suffix).
 * In static mode, files are /data/results.json, /data/sites.json, etc.
 */

import type {
  ConsistencyChecks,
  DrawsIndex,
  FHIRIndex,
  Methodology,
  Provenance,
  Results,
  Sites,
} from "../types/contracts";

const BASE = (import.meta.env.VITE_DATA_BASE as string | undefined) ?? "/api";
const STATIC = !BASE.endsWith("/api");

function path(name: string): string {
  return STATIC ? `${BASE}/${name}.json` : `${BASE}/${name}`;
}

function binPath(name: string): string {
  return STATIC ? `${BASE}/${name}` : `${BASE}/${name}`;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`);
  return res.json() as Promise<T>;
}

async function fetchBin(url: string): Promise<ArrayBuffer> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`);
  return res.arrayBuffer();
}

export async function loadResults(): Promise<Results> {
  return fetchJson(path("results"));
}

export async function loadSites(): Promise<Sites> {
  return fetchJson(path("sites"));
}

export async function loadDrawsIndex(): Promise<DrawsIndex> {
  return fetchJson(path("draws_index"));
}

export async function loadDrawsBin(): Promise<ArrayBuffer> {
  return fetchBin(binPath("draws.bin"));
}

export async function loadProvenance(): Promise<Provenance> {
  return fetchJson(path("provenance"));
}

export async function loadChecks(): Promise<ConsistencyChecks> {
  return fetchJson(path("checks"));
}

export async function loadMethodology(): Promise<Methodology> {
  return fetchJson(path("methodology"));
}

export async function loadFhirIndex(): Promise<FHIRIndex> {
  return fetchJson(path("fhir_index"));
}

export async function loadFhirBundle(filePath: string): Promise<unknown> {
  // In API mode, FHIR bundles served at /api/fhir/bundle/<name>
  if (!STATIC) {
    const name = filePath.replace("fhir/out/", "").replace(".json", "");
    return fetchJson(`${BASE}/fhir/bundle/${name}`);
  }
  return fetchJson(`${BASE}/${filePath}`);
}

export function apiBase(): string {
  return BASE;
}
