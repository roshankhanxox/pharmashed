import { MapView } from "./MapView";
import { SiteInspector } from "./SiteInspector";

export function ExploreTab() {
  return (
    <div className="flex h-full min-h-0" style={{ background: "#0c0a09" }}>
      {/* Map rail ~45% */}
      <div
        className="w-[45%] min-w-0 flex flex-col h-full"
        style={{ borderRight: "1px solid #292524" }}
      >
        <MapView />
      </div>
      {/* Inspector ~55% */}
      <div className="flex-1 min-w-0 overflow-y-auto scrollbar-none" style={{ background: "#0c0a09" }}>
        <SiteInspector />
      </div>
    </div>
  );
}
