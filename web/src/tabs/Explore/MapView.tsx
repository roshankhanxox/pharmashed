import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useStore } from "../../data/store";
import type { StyleSpecification } from "maplibre-gl";

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

export function MapView() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const fittedRef = useRef(false);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const results = useStore((s) => s.results);
  const sites = useStore((s) => s.sites);
  const selectedDrug = useStore((s) => s.selectedDrug);
  const selectedCity = useStore((s) => s.selectedCity);
  const selectedSiteId = useStore((s) => s.selectedSiteId);
  const setSelectedSiteId = useStore((s) => s.setSelectedSiteId);
  const setSelectedCity = useStore((s) => s.setSelectedCity);
  const setSelectedDrug = useStore((s) => s.setSelectedDrug);

  const drugs = results?.drugs ?? [];
  const cities = results
    ? [...new Set(results.results.map((r) => r.site_id.split("-")[0]))]
    : [];
  const citySummary = results?.city_summary ?? [];

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

    map.on("load", () => {
      map.resize();
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
          });
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

  // Rebuild markers when drug/selection changes
  useEffect(() => {
    const map = mapInstance.current;
    if (!map || !results || !sites) return;

    // Remove old markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const useOverall = selectedDrug === "all";

    for (const site of sites.sites) {
      const siteId = site.id;

      let tier: string;
      let score: number;
      let label: string;

      if (useOverall) {
        const overall = results.site_overall?.find((s) => s.site_id === siteId);
        if (!overall) continue;
        score = overall.score;
        tier = scoreTier(score);
        label = `${siteId} · top drug: ${overall.top_drug} · score ${score.toFixed(2)}`;
      } else {
        const entry = results.results.find(
          (r) => r.site_id === siteId && r.drug === selectedDrug
        );
        if (!entry) continue;
        tier = entry.tier;
        score = entry.score;
        label = `${siteId} · ${selectedDrug} · score ${score.toFixed(2)}`;
      }

      const color = TIER_COLORS[tier] ?? "#aaa";
      const r = tier === "high" ? 11 : tier === "medium" ? 8 : 5;
      const isSelected = siteId === selectedSiteId;
      const isHigh = tier === "high";

      const el = document.createElement("div");
      el.setAttribute("role", "button");
      el.setAttribute("aria-label", label);
      el.title = label;
      el.style.cssText = [
        `width:${r * 2}px`,
        `height:${r * 2}px`,
        `border-radius:50%`,
        `background:${color}`,
        `border:2px solid white`,
        `cursor:pointer`,
        `transition:transform 0.1s`,
        isSelected
          ? `outline:3px solid #3b82f6;outline-offset:2px;transform:scale(1.25)`
          : `box-shadow:0 1px 4px rgba(0,0,0,0.35)`,
        isHigh && !isSelected
          ? `box-shadow:0 0 0 4px ${color}44,0 1px 4px rgba(0,0,0,0.35)`
          : "",
      ]
        .filter(Boolean)
        .join(";");

      el.addEventListener("click", () => {
        setSelectedSiteId(siteId);
        setSelectedCity(site.city);
      });

      el.addEventListener("mouseenter", (e) => {
        const containerRect = mapContainerRef.current?.getBoundingClientRect();
        if (!containerRect) return;
        setTooltip({
          siteId,
          x: (e as MouseEvent).clientX - containerRect.left,
          y: (e as MouseEvent).clientY - containerRect.top,
        });
      });

      el.addEventListener("mousemove", (e) => {
        const containerRect = mapContainerRef.current?.getBoundingClientRect();
        if (!containerRect) return;
        setTooltip((prev) =>
          prev?.siteId === siteId
            ? { siteId, x: (e as MouseEvent).clientX - containerRect.left, y: (e as MouseEvent).clientY - containerRect.top }
            : prev
        );
      });

      el.addEventListener("mouseleave", () => {
        setTooltip(null);
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([site.lonlat[0], site.lonlat[1]])
        .addTo(map);

      markersRef.current.push(marker);
    }
  }, [results, sites, selectedDrug, selectedSiteId]);

  const C = {
    canvas:  "var(--c-canvas)",
    surface: "var(--c-surface)",
    border:  "var(--c-border)",
    text:    "var(--c-text)",
    muted:   "var(--c-muted)",
    faint:   "var(--c-faint)",
    indigo:  "var(--c-indigo)",
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
            className="text-xs font-semibold uppercase w-12 shrink-0 pt-1"
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
                  background: isActive ? "rgba(124,117,255,0.12)" : "transparent",
                  color: isActive ? C.indigo : C.muted,
                }}
              >
                {city}
                {summary && (
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
            className="text-xs font-semibold uppercase w-12 shrink-0 pt-1"
            style={{ color: C.faint, letterSpacing: "0.06em" }}
          >
            Drug
          </span>
          <div className="flex gap-1 flex-wrap">
          {(["all", ...drugs] as string[]).map((d) => (
            <button
              key={d}
              onClick={() => setSelectedDrug(d)}
              className="px-2 py-0.5 text-xs rounded transition-all shrink-0"
              style={{
                border: `1px solid ${selectedDrug === d ? C.indigo : C.border}`,
                background: selectedDrug === d ? "rgba(124,117,255,0.12)" : "transparent",
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
          <span className="w-8 shrink-0" />
          {(
            [
              { label: "High ≥0.5", color: "#ef4444", r: 8 },
              { label: "Medium ≥0.1", color: "#f59e0b", r: 6 },
              { label: "Low", color: "#22c55e", r: 4 },
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
          <span className="ml-auto text-xs" style={{ color: C.faint }}>
            score = share of draws with RQ &gt; 1
          </span>
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
            score {overall.score.toFixed(2)}
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
          </div>
        ))}
        {siteResults.length > 4 && (
          <div className="text-xs" style={{ color: "var(--c-faint)" }}>
            +{siteResults.length - 4} more drugs
          </div>
        )}
      </div>

      <div className="text-xs" style={{ color: "var(--c-faint)" }}>
        Click to inspect full profile →
      </div>
    </div>
  );
}
