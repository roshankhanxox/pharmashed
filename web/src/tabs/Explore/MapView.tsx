import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useStore } from "../../data/store";

const TIER_COLORS: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

export function MapView() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<maplibregl.Map | null>(null);

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

  useEffect(() => {
    if (!mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapRef.current,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [3.7, 48],
      zoom: 4,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapInstance.current = map;

    // Force resize after mount so MapLibre measures the container correctly
    map.on("load", () => { map.resize(); });

    // Also resize whenever the container size changes (flex layout settling)
    const ro = new ResizeObserver(() => { map.resize(); });
    if (mapRef.current) ro.observe(mapRef.current);

    return () => { ro.disconnect(); map.remove(); };
  }, []);

  // Fly to selected city
  useEffect(() => {
    if (!selectedCity || !mapInstance.current || !sites) return;
    const city = sites.cities.find((c) => c.id === selectedCity);
    if (city) {
      mapInstance.current.flyTo({ center: [city.center[0], city.center[1]], zoom: city.zoom });
    }
  }, [selectedCity, sites]);

  // Add markers when results/drug changes
  useEffect(() => {
    const map = mapInstance.current;
    if (!map || !results || !sites) return;

    // Remove existing markers
    document.querySelectorAll(".pharmashed-site-marker").forEach((el) => el.remove());

    for (const site of sites.sites) {
      const siteId = site.id;
      const entry = results.results.find(
        (r) => r.site_id === siteId && r.drug === selectedDrug
      );
      if (!entry) continue;

      const tier = entry.tier;
      const color = TIER_COLORS[tier] ?? "#aaa";
      const radius = tier === "high" ? 12 : tier === "medium" ? 9 : 6;

      const el = document.createElement("div");
      el.className = "pharmashed-site-marker";
      el.style.cssText = `
        width:${radius * 2}px;height:${radius * 2}px;
        border-radius:50%;background:${color};opacity:0.85;
        border:2px solid white;cursor:pointer;
        ${siteId === selectedSiteId ? "box-shadow:0 0 0 3px #3b82f6;" : ""}
      `;
      el.title = `${siteId} — ${site.name}\nScore: ${entry.score.toFixed(3)}`;

      el.addEventListener("click", () => {
        setSelectedSiteId(siteId);
        setSelectedCity(site.city);
      });

      new maplibregl.Marker({ element: el })
        .setLngLat([site.lonlat[0], site.lonlat[1]])
        .addTo(map);
    }
  }, [results, sites, selectedDrug, selectedSiteId]);

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="p-2 border-b border-neutral-200 dark:border-neutral-800 flex flex-wrap gap-2 items-center bg-white dark:bg-neutral-950">
        <div className="flex gap-1 flex-wrap">
          {cities.map((city) => {
            const summary = citySummary.find((c) => c.city === city);
            return (
              <button
                key={city}
                onClick={() => setSelectedCity(city)}
                className={`px-2 py-1 text-xs rounded-md border transition-colors ${
                  selectedCity === city
                    ? "border-blue-500 bg-blue-50 text-blue-700"
                    : "border-neutral-200 hover:border-blue-300 text-neutral-600"
                }`}
              >
                {city}
                {summary && (
                  <span className="ml-1 text-neutral-400">
                    {summary.high > 0 && <span className="text-red-500">{summary.high}H</span>}
                    {summary.medium > 0 && <span className="text-yellow-500 ml-0.5">{summary.medium}M</span>}
                    {summary.low > 0 && <span className="text-green-500 ml-0.5">{summary.low}L</span>}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <div className="flex gap-1 flex-wrap ml-auto">
          <button
            onClick={() => setSelectedDrug("all")}
            className={`px-2 py-1 text-xs rounded-md border transition-colors ${
              selectedDrug === "all"
                ? "border-blue-500 bg-blue-50 text-blue-700"
                : "border-neutral-200 hover:border-blue-300 text-neutral-600"
            }`}
          >
            All
          </button>
          {drugs.map((d) => (
            <button
              key={d}
              onClick={() => setSelectedDrug(d)}
              className={`px-2 py-1 text-xs rounded-md border transition-colors ${
                selectedDrug === d
                  ? "border-blue-500 bg-blue-50 text-blue-700"
                  : "border-neutral-200 hover:border-blue-300 text-neutral-600"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Map — needs explicit height for MapLibre to render tiles */}
      <div ref={mapRef} style={{ flex: 1, minHeight: 0, height: "100%" }} />
    </div>
  );
}
