export function LoadingView({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-32 text-sm animate-pulse"
      style={{ color: "#6b6460" }}>
      {label}
    </div>
  );
}

export function EmptyView({ reason }: { reason: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-32 text-sm px-4 text-center"
      style={{ color: "#6b6460" }}>
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
