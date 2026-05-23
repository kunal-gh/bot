// src/lib/utils.ts

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const n = Number(val);
  if (isNaN(n)) return String(val);
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return n.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return n.toFixed(2).replace(/\.?0+$/, "");
}

export function formatDate(val: unknown): string {
  if (!val) return "—";
  const d = new Date(String(val));
  if (isNaN(d.getTime())) return String(val);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function getColumnType(val: unknown): "number" | "date" | "boolean" | "string" {
  if (val === null || val === undefined) return "string";
  if (typeof val === "number") return "number";
  if (typeof val === "boolean") return "boolean";
  const s = String(val);
  if (!isNaN(Number(s)) && s.trim() !== "") return "number";
  if (!isNaN(Date.parse(s)) && s.length > 5) return "date";
  return "string";
}

export const SAMPLE_QUERIES = [
  "Which products had the highest revenue?",
  "Show me the top 5 items by total sales",
  "Forecast revenue for the next 30 days",
  "Detect anomalies in my sales data",
  "Segment customers by order value",
  "Show revenue trend over time",
  "What is the average order value?",
  "Which orders had the highest total value?",
];

export const INTENT_COLORS: Record<string, string> = {
  lookup: "badge-cyan",
  aggregation: "badge-purple",
  comparison: "badge-amber",
  trend: "badge-green",
  top_n: "badge-purple",
  join_based: "badge-cyan",
  derived_metric: "badge-green",
  anomaly_detection: "badge-amber",
  anomaly_explain: "badge-amber",
  forecast: "badge-cyan",
  cluster: "badge-green",
};
