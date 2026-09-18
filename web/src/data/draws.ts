/**
 * Float32Array view over the draws.bin binary.
 * draw = RQ value; one block per (site, drug) entry in draws_index.json.
 */

import type { DrawsIndex } from "../types/contracts";

export interface DrawsView {
  slice(siteId: string, drug: string): Float32Array;
}

export function createDrawsView(index: DrawsIndex, buf: ArrayBuffer): DrawsView {
  const all = new Float32Array(buf);

  const lookup = new Map<string, { offset: number; count: number }>();
  for (const entry of index.entries) {
    lookup.set(`${entry.site_id}:${entry.drug}`, {
      offset: entry.offset,
      count: entry.count,
    });
  }

  return {
    slice(siteId: string, drug: string): Float32Array {
      const key = `${siteId}:${drug}`;
      const loc = lookup.get(key);
      if (!loc) return new Float32Array(0);
      return all.slice(loc.offset, loc.offset + loc.count);
    },
  };
}
