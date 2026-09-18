import { MapView } from "./MapView";
import { SiteInspector } from "./SiteInspector";

export function ExploreTab() {
  return (
    <div className="flex h-full min-h-0">
      {/* Map rail ~45% */}
      <div className="w-[45%] min-w-0 border-r border-neutral-200 dark:border-neutral-800 flex flex-col h-full">
        <MapView />
      </div>
      {/* Inspector ~55% */}
      <div className="flex-1 min-w-0 overflow-y-auto">
        <SiteInspector />
      </div>
    </div>
  );
}
