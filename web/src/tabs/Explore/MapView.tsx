import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { TIER_LABEL, TIER_LEGEND } from "../../data/copy";
import { useStore } from "../../data/store";
import type { StyleSpecification } from "maplibre-gl";
// MapLibre 6 runs GeoJSON layers in a worker file that imports a sibling chunk. Vite must bundle it
// as a self-contained file (?worker&url); without this the production build ships no worker and the
// site glows never render, silently.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";

maplibregl.setWorkerUrl(workerUrl);

interface TooltipState {
  siteId: string;
  x: number;
  y: number;
}

const TIER_COLORS: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

function scoreTier(score: number): "high" | "medium" | "low" {
  if (score >= 0.5) return "high";
  if (score >= 0.1) return "medium";
  return "low";
}

const BASEMAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const SITES_SOURCE = "sites";

/** Colour expression keyed on the feature's tier. */
const tierColor = ["match", ["get", "tier"], "high", TIER_COLORS.high, "medium", TIER_COLORS.medium, TIER_COLORS.low];

/** Radius expression keyed on tier, growing with zoom so a glow keeps its look at every scale. */
function glowRadius(high: number, medium: number, low: number) {
  return ["match", ["get", "tier"], "high", high, "medium", medium, low];
}

interface SiteProps {
  id: string;
  city: string;
  tier: "high" | "medium" | "low";
}

/** One site as a GeoJSON point feature (the map source holds these). */
interface SiteFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: SiteProps;
}

export function MapView() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<maplibregl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const fittedRef = useRef(false);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const results = useStore((s) => s.results);
  const sites = useStore((s) => s.sites);
  const selectedDrug = useStore((s) => s.selectedDrug);
  const selectedCity = useStore((s) => s.selectedCity);
  const selectedSiteId = useStore((s) => s.selectedSiteId);
  const setSelectedCity = useStore((s) => s.setSelectedCity);
  const setSelectedDrug = useStore((s) => s.setSelectedDrug);
  const audience = useStore((s) => s.audience);
  const citizen = audience === "citizen";

  const drugs = results?.drugs ?? [];
  const cities = results
    ? [...new Set(results.results.map((r) => r.site_id.split("-")[0]))]
    : [];
  const citySummary = results?.city_summary ?? [];
  const cityName = (id: string) => sites?.cities.find((c) => c.id === id)?.name ?? id;

  // Initialise map once
  useEffect(() => {
    if (!mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapRef.current,
      style: BASEMAP_STYLE,
      center: [3.7, 48],
      zoom: 4,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapInstance.current = map;
    // Dev only: lets browser tests project site coordinates to screen positions (sites are canvas, not DOM).
    if (import.meta.env.DEV) (window as unknown as { __pharmaMap?: maplibregl.Map }).__pharmaMap = map;

    map.on("load", () => {
      map.resize();

      // Sites: a blurred glow per site (the heat feel), a small solid core (shape cue, not colour-only),
      // and a ring on the selected site. One source, updated whenever the drug filter changes.
      map.addSource(SITES_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "site-glow",
        type: "circle",
        source: SITES_SOURCE,
        paint: {
          "circle-color": tierColor as never,
          "circle-blur": 1,
          "circle-opacity": ["match", ["get", "tier"], "high", 0.85, "medium", 0.72, 0.55] as never,
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            8, glowRadius(22, 18, 14),
            11, glowRadius(44, 34, 24),
            13, glowRadius(78, 60, 44),
            15, glowRadius(120, 92, 68),
            17, glowRadius(170, 130, 96),
          ] as never,
        },
      });
      map.addLayer({
        id: "site-core",
        type: "circle",
        source: SITES_SOURCE,
        paint: {
          "circle-color": tierColor as never,
          "circle-radius": glowRadius(7, 6, 5) as never,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });
      map.addLayer({
        id: "site-selected",
        type: "circle",
        source: SITES_SOURCE,
        filter: ["==", ["get", "id"], ""],
        paint: {
          "circle-color": "#1c1917",
          "circle-opacity": 0,
          "circle-radius": 13,
          "circle-stroke-color": "#1c1917",
          "circle-stroke-width": 3,
        },
      });

      // With overlapping glows several features sit under the cursor: pick the nearest site.
      const nearest = (e: maplibregl.MapLayerMouseEvent): maplibregl.MapGeoJSONFeature | null => {
        let best: maplibregl.MapGeoJSONFeature | null = null;
        let bestDist = Infinity;
        for (const f of e.features ?? []) {
          if (f.geometry.type !== "Point") continue;
          const [lng, lat] = f.geometry.coordinates;
          const pt = map.project([lng, lat]);
          const d = Math.hypot(pt.x - e.point.x, pt.y - e.point.y);
          if (d < bestDist) { best = f; bestDist = d; }
        }
        return best;
      };

      map.on("mousemove", "site-glow", (e) => {
        const f = nearest(e);
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const rect = mapContainerRef.current?.getBoundingClientRect();
        if (!rect) return;
        // Keep the tooltip (about 240 x 200 px) inside the map so it is never cut off at an edge.
        setTooltip({
          siteId: (f.properties as SiteProps).id,
          x: Math.min(e.originalEvent.clientX - rect.left, rect.width - 260),
          y: Math.min(e.originalEvent.clientY - rect.top, rect.height - 210),
        });
      });
      map.on("mouseleave", "site-glow", () => {
        map.getCanvas().style.cursor = "";
        setTooltip(null);
      });
      map.on("click", "site-glow", (e) => {
        const f = nearest(e);
        if (!f) return;
        const props = f.properties as SiteProps;
        useStore.getState().setSelectedSiteId(props.id);
        useStore.getState().setSelectedCity(props.city);
      });

      setMapReady(true);
      // Streams layer — silently skip if endpoint not available
      const BASE = (import.meta.env.VITE_DATA_BASE as string | undefined) ?? "/api";
      const STATIC = BASE !== "/api";
      const streamsUrl = STATIC ? `${BASE}/streams.geojson` : `${BASE}/streams`;
      fetch(streamsUrl)
        .then((r) => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
        .then((geojson) => {
          if (map.getSource("streams")) return;
          map.addSource("streams", { type: "geojson", data: geojson });
          map.addLayer({
            id: "streams",
            type: "line",
            source: "streams",
            paint: { "line-color": "#2563eb", "line-width": 1.5, "line-opacity": 0.6 },
          }, "site-glow");
        })
        .catch(() => { /* streams.geojson not available — skip */ });
    });

    const ro = new ResizeObserver(() => {
      map.resize();
    });
    if (mapRef.current) ro.observe(mapRef.current);

    return () => {
      ro.disconnect();
      map.remove();
    };
  }, []);

  // Fly to selected city
  useEffect(() => {
    if (!selectedCity || !mapInstance.current || !sites) return;
    const city = sites.cities.find((c) => c.id === selectedCity);
    if (city) {
      mapInstance.current.flyTo({
        center: [city.center[0], city.center[1]],
        zoom: city.zoom,
      });
    }
  }, [selectedCity, sites]);

  // Fly to Toulouse (TLS) on first load — most high-priority sites, dramatic opening view
  useEffect(() => {
    const map = mapInstance.current;
    if (!map || fittedRef.current) return;
    const fly = () => {
      map.flyTo({ center: [1.4442, 43.6047], zoom: 12 });
      fittedRef.current = true;
    };
    if (map.loaded()) fly();
    else map.once("load", fly);
  }, []);

  // Push the visible sites (for the chosen drug, or each site's overall score) into the map source.
  useEffect(() => {
    const map = mapInstance.current;
    if (!map || !mapReady || !results || !sites) return;

    const features: SiteFeature[] = [];
    for (const site of sites.sites) {
      let score: number | undefined;
      let tier: SiteProps["tier"] | undefined;
      if (selectedDrug === "all") {
        score = results.site_overall?.find((o) => o.site_id === site.id)?.score;
        tier = score === undefined ? undefined : scoreTier(score);
      } else {
        const entry = results.results.find((r) => r.site_id === site.id && r.drug === selectedDrug);
        score = entry?.score;
        tier = entry?.tier as SiteProps["tier"] | undefined;
      }
      if (score === undefined || !tier) continue;
      features.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: [site.lonlat[0], site.lonlat[1]] },
        properties: { id: site.id, city: site.city, tier },
      });
    }
    (map.getSource(SITES_SOURCE) as maplibregl.GeoJSONSource | undefined)?.setData({
      type: "FeatureCollection",
      features,
    });
  }, [mapReady, results, sites, selectedDrug]);

  // Ring the selected site.
  useEffect(() => {
    const map = mapInstance.current;
    if (!map || !mapReady) return;
    map.setFilter("site-selected", ["==", ["get", "id"], selectedSiteId ?? ""]);
  }, [mapReady, selectedSiteId]);

  const C = {
    canvas:  "var(--c-canvas)",
    surface: "var(--c-surface)",
    border:  "var(--c-border)",
    text:    "var(--c-text)",
    muted:   "var(--c-muted)",
    faint:   "var(--c-faint)",
    indigo:  "var(--c-accent)",
  } as const;

  return (
    <div className="flex flex-col h-full" style={{ background: C.canvas }}>
      {/* Controls bar */}
      <div
        className="px-3 py-2 flex flex-col gap-1.5 shrink-0"
        style={{ borderBottom: `1px solid ${C.border}`, background: C.surface }}
      >
        {/* Cities */}
        <div className="flex gap-1.5 items-start min-w-0">
          <span
            className="text-xs font-semibold uppercase w-20 shrink-0 pt-1"
            style={{ color: C.faint, letterSpacing: "0.06em" }}
          >
            City
          </span>
          <div className="flex gap-1.5 flex-wrap">
          {cities.map((city) => {
            const summary = citySummary.find((c) => c.city === city);
            const isActive = selectedCity === city;
            return (
              <button
                key={city}
                onClick={() => setSelectedCity(isActive ? null : city)}
                className="px-2 py-0.5 text-xs rounded transition-all shrink-0"
                style={{
                  border: `1px solid ${isActive ? C.indigo : C.border}`,
                  background: isActive ? "var(--c-accent-tint)" : "transparent",
                  color: isActive ? C.indigo : C.muted,
                }}
              >
                {cityName(city)}
                {summary && !citizen && (
                  <span className="ml-1.5 space-x-0.5">
                    {summary.high > 0 && (
                      <span style={{ color: "var(--c-danger-text)", fontWeight: 600 }}>{summary.high}H</span>
                    )}
                    {summary.medium > 0 && (
                      <span style={{ color: "var(--c-warn-text)", fontWeight: 600 }}>{summary.medium}M</span>
                    )}
                    {summary.low > 0 && (
                      <span style={{ color: "var(--c-ok-text)", fontWeight: 600 }}>{summary.low}L</span>
                    )}
                  </span>
                )}
              </button>
            );
          })}
          </div>
        </div>

        {/* Drugs */}
        <div className="flex gap-1.5 items-start min-w-0">
          <span
            className="text-xs font-semibold uppercase w-20 shrink-0 pt-1"
            style={{ color: C.faint, letterSpacing: "0.06em" }}
          >
            {citizen ? "Medicine" : "Drug"}
          </span>
          <div className="flex gap-1 flex-wrap">
          {(["all", ...drugs] as string[]).map((d) => (
            <button
              key={d}
              onClick={() => setSelectedDrug(d)}
              className="px-2 py-0.5 text-xs rounded transition-all shrink-0"
              style={{
                border: `1px solid ${selectedDrug === d ? C.indigo : C.border}`,
                background: selectedDrug === d ? "var(--c-accent-tint)" : "transparent",
                color: selectedDrug === d ? C.indigo : C.muted,
              }}
            >
              {d === "all" ? "All" : d}
            </button>
          ))}
          </div>
        </div>

        {/* Tier legend */}
        <div className="flex gap-4 items-center">
          <span className="w-20 shrink-0" />
          {(
            [
              { label: citizen ? TIER_LEGEND.high : "High ≥0.5", color: "#ef4444", r: 8 },
              { label: citizen ? TIER_LEGEND.medium : "Medium ≥0.1", color: "#f59e0b", r: 6 },
              { label: citizen ? TIER_LEGEND.low : "Low", color: "#22c55e", r: 4 },
            ] as const
          ).map(({ label, color, r }) => (
            <span key={label} className="flex items-center gap-1.5 text-xs" style={{ color: C.faint }}>
              <span
                style={{
                  display: "inline-block",
                  width: r * 2,
                  height: r * 2,
                  borderRadius: "50%",
                  background: color,
                  border: `1.5px solid ${C.border}`,
                  boxShadow: "0 1px 2px rgba(0,0,0,0.4)",
                  flexShrink: 0,
                }}
              />
              {label}
            </span>
          ))}
          {!citizen && (
            <span className="ml-auto text-xs" style={{ color: C.faint }}>
              score = share of draws with RQ &gt; 1
            </span>
          )}
        </div>

        {/* A glow is a site, not a surface: the model scores 105 points and does not interpolate between them. */}
        <div className="text-xs" style={{ color: C.faint }}>
          {citizen
            ? "Each glow marks one place we look at. Colour is not estimated between places."
            : "Each glow is one monitoring site. Scores are not interpolated between sites. H / M / L after a city = its number of high / medium / low priority sites."}
        </div>
      </div>

      {/* Map canvas + tooltip overlay */}
      <div ref={mapContainerRef} className="flex-1 min-h-0 relative" style={{ background: "var(--c-surface)" }}>
        <div ref={mapRef} className="w-full h-full" />
        {tooltip && results && (
          <SiteTooltip
            siteId={tooltip.siteId}
            x={tooltip.x}
            y={tooltip.y}
            results={results}
          />
        )}
      </div>
    </div>
  );
}

/* ── Hover tooltip ─────────────────────────────────────────────────────────── */

const TIER_DOT: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

function SiteTooltip({
  siteId,
  x,
  y,
  results,
}: {
  siteId: string;
  x: number;
  y: number;
  results: import("../../types/contracts").Results;
}) {
  const citizen = useStore((s) => s.audience) === "citizen";
  const siteResults = results.results
    .filter((r) => r.site_id === siteId)
    .sort((a, b) => b.score - a.score);

  const overall = results.site_overall?.find((s) => s.site_id === siteId);
  const topDrugs = siteResults.slice(0, 4);

  // Position tooltip so it stays inside the container
  const OFFSET = 14;
  const style: React.CSSProperties = {
    position: "absolute",
    left: x + OFFSET,
    top: y + OFFSET,
    pointerEvents: "none",
    zIndex: 1000,
    background: "var(--c-surface)",
    border: "1px solid var(--c-border)",
    borderRadius: 10,
    padding: "10px 12px",
    minWidth: 200,
    maxWidth: 240,
    boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
  };

  return (
    <div style={style}>
      {/* Header */}
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <span
          className="text-xs font-semibold"
          style={{ color: "var(--c-text)" }}
        >
          {siteId}
        </span>
        {overall && (
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              background: scoreTier(overall.score) === "high" ? "rgba(239,68,68,0.15)" : scoreTier(overall.score) === "medium" ? "rgba(245,158,11,0.15)" : "rgba(34,197,94,0.15)",
              color: TIER_DOT[scoreTier(overall.score)] ?? "#aaa",
            }}
          >
            {citizen ? TIER_LABEL[scoreTier(overall.score)] : `score ${overall.score.toFixed(2)}`}
          </span>
        )}
      </div>

      {/* Drug rows */}
      <div className="flex flex-col gap-1 mb-2.5">
        {topDrugs.map((r) => (
          <div key={r.drug} className="flex items-center gap-2">
            <span
              style={{
                display: "inline-block",
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: TIER_DOT[r.tier] ?? "#aaa",
                flexShrink: 0,
              }}
            />
            <span className="text-xs flex-1 truncate" style={{ color: "var(--c-muted)" }}>
              {r.drug}
            </span>
            {citizen ? (
              <span className="text-xs" style={{ color: "var(--c-muted)" }}>
                {TIER_LABEL[scoreTier(r.score)]}
              </span>
            ) : (
              <>
                <span
                  className="text-xs tabular-nums"
                  style={{ color: TIER_DOT[r.tier] ?? "#aaa" }}
                >
                  {r.score.toFixed(2)}
                </span>
                <span
                  className="text-xs"
                  style={{ color: "var(--c-faint)" }}
                >
                  RQ {r.rq.p50.toFixed(1)}
                </span>
              </>
            )}
          </div>
        ))}
        {siteResults.length > 4 && (
          <div className="text-xs" style={{ color: "var(--c-faint)" }}>
            +{siteResults.length - 4} more {citizen ? "medicines" : "drugs"}
          </div>
        )}
      </div>

      <div className="text-xs" style={{ color: "var(--c-faint)" }}>
        {citizen ? "Tap to see details →" : "Click to inspect full profile →"}
      </div>
    </div>
  );
}
