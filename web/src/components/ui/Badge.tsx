"use client";

// src/components/ui/Badge.tsx
import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "purple" | "cyan" | "green" | "amber" | "red";
  className?: string;
}

export function Badge({ children, variant = "purple", className }: BadgeProps) {
  const variantMap = {
    purple: "badge-purple",
    cyan: "badge-cyan",
    green: "badge-green",
    amber: "badge-amber",
    red: "badge-red",
  };
  return (
    <span className={cn("badge", variantMap[variant], className)}>
      {children}
    </span>
  );
}
