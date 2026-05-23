"use client";

// src/components/ui/AnimatedOrbs.tsx
export function AnimatedOrbs() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="orb orb-purple" />
      <div className="orb orb-cyan" />
      {/* Subtle grid overlay */}
      <div className="absolute inset-0 bg-grid opacity-50" />
    </div>
  );
}
