"use client";

// src/components/ui/LoadingDots.tsx
export function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </div>
  );
}

export function SkeletonLine({ width = "100%" }: { width?: string }) {
  return (
    <div
      className="shimmer h-3 rounded-full"
      style={{ width }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="glass rounded-2xl p-5 space-y-3">
      <SkeletonLine width="60%" />
      <SkeletonLine width="90%" />
      <SkeletonLine width="75%" />
    </div>
  );
}
