export function LoadingView({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-32 text-sm animate-pulse"
      style={{ color: "#948e89" }}>
      {label}
    </div>
  );
}

export function EmptyView({ reason }: { reason: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-32 text-sm px-4 text-center"
      style={{ color: "#948e89" }}>
      {reason}
    </div>
  );
}

export function InvalidView({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-32 text-sm px-4 text-center"
      style={{ color: "#f87171" }}>
      <span>⚠ {message}</span>
    </div>
  );
}
