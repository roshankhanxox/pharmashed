export function LoadingView({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-32 text-neutral-400 text-sm">
      <span className="animate-pulse">{label}</span>
    </div>
  );
}

export function EmptyView({ reason }: { reason: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-32 text-neutral-400 text-sm px-4 text-center">
      {reason}
    </div>
  );
}

export function InvalidView({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-32 text-red-500 text-sm px-4 text-center">
      <span>⚠ {message}</span>
    </div>
  );
}
