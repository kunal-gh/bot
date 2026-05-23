"use client";

import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "purple" | "cyan" | "green" | "amber" | "red";
  className?: string;
}

export function Badge({ children, variant = "purple", className }: BadgeProps) {
  const variantStyles = {
    purple: "bg-zinc-900 border-white/5 text-zinc-300",
    cyan: "bg-zinc-900 border-white/5 text-zinc-400",
    green: "bg-emerald-950/20 border-emerald-500/20 text-emerald-400",
    amber: "bg-amber-950/20 border-amber-500/20 text-amber-400",
    red: "bg-rose-950/20 border-rose-500/20 text-rose-400",
  };

  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg border text-[10px] font-semibold select-none transition-colors duration-150",
      variantStyles[variant],
      className
    )}>
      {children}
    </span>
  );
}
