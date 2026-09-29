import { MapView } from "./MapView";
import { SiteInspector } from "./SiteInspector";
import { useSmoothScroll } from "../../hooks/useSmoothScroll";

export function ExploreTab() {
  const inspectorRef = useSmoothScroll();

  return (
    <div className="flex h-full min-h-0" style={{ background: "var(--c-canvas)" }}>
      {/* Map rail ~45% */}
      <div
        className="w-[45%] min-w-0 flex flex-col h-full"
        style={{ borderRight: "1px solid var(--c-border)" }}
      >
        <MapView />
      </div>
      {/* Inspector ~55% */}
      <div ref={inspectorRef} className="flex-1 min-w-0 overflow-y-auto scrollbar-none" style={{ background: "var(--c-canvas)" }}>
        <SiteInspector />
      </div>
    </div>
  );
}
