/**
 * Generated from contracts/schemas/*.schema.json by scripts/gen-types.mjs.
 * Do not edit by hand -- run `pnpm run gen:types`.
 */

// ---- checks.schema.json ----
/**
 * checks.json — output of the pre-registered consistency checks C1-C5 against frozen predictions (M12).
 */
export interface ConsistencyChecks {
  meta: {
    frozen_tag: string;
    frozen_sha256: string;
    generated_at: string;
  };
  circularity_statement: string;
  /**
   * @minItems 5
   * @maxItems 5
   */
  checks: [
    {
      id: "C1" | "C2" | "C3" | "C4" | "C5";
      status: "pass" | "fail" | "unavailable";
      reason: string | null;
      /**
       * Check-specific payload (scatter points for C1, orders + tau for C2/C3, rows for C4, rank-change table for C5). Shape documented in IMPLEMENTATION.md M12/M21, not constrained further here.
       */
      data: {};
    },
    {
      id: "C1" | "C2" | "C3" | "C4" | "C5";
      status: "pass" | "fail" | "unavailable";
      reason: string | null;
      /**
       * Check-specific payload (scatter points for C1, orders + tau for C2/C3, rows for C4, rank-change table for C5). Shape documented in IMPLEMENTATION.md M12/M21, not constrained further here.
       */
      data: {};
    },
    {
      id: "C1" | "C2" | "C3" | "C4" | "C5";
      status: "pass" | "fail" | "unavailable";
      reason: string | null;
      /**
       * Check-specific payload (scatter points for C1, orders + tau for C2/C3, rows for C4, rank-change table for C5). Shape documented in IMPLEMENTATION.md M12/M21, not constrained further here.
       */
      data: {};
    },
    {
      id: "C1" | "C2" | "C3" | "C4" | "C5";
      status: "pass" | "fail" | "unavailable";
      reason: string | null;
      /**
       * Check-specific payload (scatter points for C1, orders + tau for C2/C3, rows for C4, rank-change table for C5). Shape documented in IMPLEMENTATION.md M12/M21, not constrained further here.
       */
      data: {};
    },
    {
      id: "C1" | "C2" | "C3" | "C4" | "C5";
      status: "pass" | "fail" | "unavailable";
      reason: string | null;
      /**
       * Check-specific payload (scatter points for C1, orders + tau for C2/C3, rows for C4, rank-change table for C5). Shape documented in IMPLEMENTATION.md M12/M21, not constrained further here.
       */
      data: {};
    }
  ];
}

// ---- draws.schema.json ----
/**
 * draws_index.json — describes the binary layout of draws.bin: little-endian float32 RQ draws, one block per result entry, addressed by offset.
 */
export interface DrawsIndex {
  dtype: "float32";
  endianness: "little";
  n_stored: number;
  entries: {
    site_id: string;
    drug: string;
    offset: number;
    count: number;
  }[];
}

// ---- fhir_index.schema.json ----
/**
 * fhir_index.json — resource counts, bundle list, validator status and query-demo counts (M14/M15).
 */
export interface FHIRIndex {
  meta: {
    generated_at: string;
  };
  resource_counts: {
    [k: string]: number;
  };
  bundles: {
    name: string;
    path: string;
    resource_type: string;
    count: number;
    source?: string | null;
    description?: string | null;
  }[];
  /**
   * Counts and credit for the OneAquaHealth IG's own example resources co-hosted with PharmaShed bundles (D38).
   */
  oah_example_counts?: {
    Location: number;
    Organization: number;
    Observation: number;
    source: string;
    note: string;
  } | null;
  validation: {
    status: "pass" | "fail" | "unknown";
    errors: number;
    warnings: number;
    validator_version: string | null;
    ran_at: string | null;
    ci_log_url: string | null;
  };
  query_demo: {
    laboratory: QueryResult;
    model_prediction: QueryResult;
  };
}
export interface QueryResult {
  query: string;
  count: number;
}

// ---- methodology.schema.json ----
/**
 * methodology.json — model stages, priors table, identifiability text, ablation rankings (M10/M11).
 */
export interface Methodology {
  meta: {
    generated_at: string;
  };
  /**
   * @minItems 1
   */
  stages: [
    {
      id: string;
      name: string;
      symbol: string;
      prior_summary: string;
      provenance_key: string;
    },
    ...{
      id: string;
      name: string;
      symbol: string;
      prior_summary: string;
      provenance_key: string;
    }[]
  ];
  priors_table: {
    param: string;
    distribution: string;
    range: string;
    unit: string;
    status: "sourced" | "assumption";
    source_url: string | null;
    shape: string;
  }[];
  identifiability_text: string;
  ablations: {
    variants: ("full" | "pop_only" | "wwtp_only")[];
    per_city: {
      city: string;
      variant: "full" | "pop_only" | "wwtp_only";
      ranking: string[];
    }[];
  };
}

// ---- provenance.schema.json ----
/**
 * provenance.json — keyed lookup for every ⓘ in the UI, indexed by provenance_keys from results.json (e.g. 'param:irbesartan:ddd_g', 'prior:lambda', 'cons:FR:irbesartan').
 */
export interface Provenance {
  [k: string]: {
    label: string;
    value: number | string | null;
    unit: string | null;
    distribution: string | null;
    source_title: string | null;
    source_url: string | null;
    source_note: string | null;
    status: "sourced" | "assumption" | "illustrative" | "todo";
  };
}

// ---- results.schema.json ----
export type FlipStep = {
  param: string;
  multiplier: number;
  to_tier: "high" | "medium" | "low";
} | null;

/**
 * results.json — Monte Carlo model output per site x drug (M08-M11).
 */
export interface Results {
  meta: {
    engine_version: string;
    generated_at: string;
    seed: number;
    n_draws: number;
    n_stored: number;
    variant: "full" | "pop_only" | "wwtp_only";
    dev_placeholders: boolean;
    frozen_tag: string | null;
    param_count: number;
    all_params_cited: boolean;
  };
  /**
   * @minItems 1
   */
  drugs: [string, ...string[]];
  results: ResultEntry[];
  site_overall: {
    site_id: string;
    score: number;
    top_drug: string;
    rank_in_city: number;
  }[];
  city_summary: {
    city: string;
    high: number;
    medium: number;
    low: number;
  }[];
}
export interface ResultEntry {
  site_id: string;
  drug: string;
  pec_ng_l: PercentileTriplet;
  rq: PercentileTriplet;
  pnec_ng_l: number;
  lod_ng_l: number;
  score: number;
  tier: "high" | "medium" | "low";
  lod_share: number;
  rank_in_city: number;
  n_in_city: number;
  drivers: {
    param: string;
    rho: number;
  }[];
  driver_sentence: string;
  flip: {
    up: FlipStep;
    down: FlipStep;
  };
  histogram: {
    log10_edges: number[];
    counts: number[];
  };
  draws: {
    offset: number;
    count: number;
  };
  provenance_keys: string[];
  fhir_ids: {
    prediction: string;
  };
}
export interface PercentileTriplet {
  p5: number;
  p50: number;
  p95: number;
}

// ---- sites.schema.json ----
/**
 * sites.json — hand-placed synthetic sites and their cities (M04).
 */
export interface Sites {
  meta: {
    generated_at: string;
    synthetic: true;
  };
  /**
   * @minItems 1
   */
  cities: [
    {
      id: string;
      name: string;
      country: string;
      /**
       * @minItems 2
       * @maxItems 2
       */
      center: [number, number];
      zoom: number;
    },
    ...{
      id: string;
      name: string;
      country: string;
      /**
       * @minItems 2
       * @maxItems 2
       */
      center: [number, number];
      zoom: number;
    }[]
  ];
  /**
   * @minItems 1
   */
  sites: [
    {
      id: string;
      city: string;
      name: string;
      /**
       * @minItems 2
       * @maxItems 2
       */
      lonlat: [number, number];
      synthetic: true;
      size_class: "S" | "M" | "L";
      w: 0 | 1;
      valid: boolean;
      population_buffer: number;
      population_source_key: string;
    },
    ...{
      id: string;
      city: string;
      name: string;
      /**
       * @minItems 2
       * @maxItems 2
       */
      lonlat: [number, number];
      synthetic: true;
      size_class: "S" | "M" | "L";
      w: 0 | 1;
      valid: boolean;
      population_buffer: number;
      population_source_key: string;
    }[]
  ];
}
