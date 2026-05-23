"use client";

// src/components/ResultChart.tsx
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, Cell,
} from "recharts";
import { formatNumber } from "@/lib/utils";

interface ResultChartProps {
  data: Record<string, unknown>[];
  intent: string;
}

const COLORS = ["#7c3aed", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#0ea5e9"];
const CLUSTER_COLORS = ["#7c3aed", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"];

// Custom Tooltip
const CustomTooltip = ({ active, payload, label }: {active?: boolean; payload?: Array<{name: string; value: unknown; color: string}>; label?: string}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-strong rounded-xl p-3 shadow-2xl text-xs min-w-[140px]">
      {label && <p className="text-slate-400 mb-1.5 font-medium">{label}</p>}
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 mb-0.5">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
          <span className="text-slate-400 capitalize">{p.name}:</span>
          <span className="text-white font-semibold ml-auto">
            {typeof p.value === "number" ? formatNumber(p.value) : String(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
};

export function ResultChart({ data, intent }: ResultChartProps) {
  if (!data || data.length === 0) return null;

  const keys = Object.keys(data[0]);
  const dateKey = keys.find(k =>
    ["date", "day", "month", "year", "time", "created_at", "ordered_at", "period"].some(d => k.toLowerCase().includes(d))
  );
  const numericKeys = keys.filter(k => {
    const val = data.find(r => r[k] !== null)?.[k];
    return typeof val === "number" || (!isNaN(Number(val)) && String(val).trim() !== "");
  });
  const categoryKey = keys.find(k => k !== dateKey && !numericKeys.includes(k));

  const isAnomalyData = keys.includes("_is_anomaly");
  const isForecastData = keys.includes("_is_forecast");
  const isClusterData = keys.includes("_cluster_id");

  const chartData = data.slice(0, 200).map(row => {
    const out: Record<string, unknown> = {};
    for (const k of keys) {
      out[k] = typeof row[k] === "number"
        ? Number(row[k])
        : row[k];
    }
    return out;
  });

  // Forecast → Line Chart with shaded forecast region
  if (intent === "forecast" || isForecastData) {
    const xKey = dateKey || keys[0];
    const yKey = numericKeys.find(k => k !== "_is_forecast") || numericKeys[0];
    if (!yKey) return null;
    return (
      <div className="w-full h-64">
        <p className="text-[10px] uppercase tracking-widest text-cyan-400 mb-2 font-semibold">📈 Forecast</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: 20, bottom: 4, left: 0 }}>
            <defs>
              <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey={xKey} tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Line
              dataKey={yKey}
              stroke="#7c3aed"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#7c3aed", stroke: "#fff", strokeWidth: 1 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Anomaly → Scatter Chart with anomalies highlighted
  if (isAnomalyData && numericKeys.length >= 2) {
    const xKey = numericKeys[0];
    const yKey = numericKeys[1];
    return (
      <div className="w-full h-64">
        <p className="text-[10px] uppercase tracking-widest text-amber-400 mb-2 font-semibold">
          🔍 Anomaly Detection — <span className="text-amber-300">{data.filter(r => r._is_anomaly).length} outliers found</span>
        </p>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 4, right: 20, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey={xKey} name={xKey} tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <YAxis dataKey={yKey} name={yKey} tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Scatter data={chartData} shape={(props: {cx?: number; cy?: number; payload?: Record<string, unknown>}) => {
              const isAnomaly = props.payload?._is_anomaly;
              return (
                <circle
                  cx={props.cx}
                  cy={props.cy}
                  r={isAnomaly ? 7 : 4}
                  fill={isAnomaly ? "#f59e0b" : "#7c3aed"}
                  stroke={isAnomaly ? "#fcd34d" : "transparent"}
                  strokeWidth={isAnomaly ? 1.5 : 0}
                  opacity={isAnomaly ? 1 : 0.6}
                />
              );
            }} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Cluster → Scatter with cluster colours
  if (isClusterData && numericKeys.length >= 2) {
    const xKey = numericKeys[0];
    const yKey = numericKeys[1];
    return (
      <div className="w-full h-64">
        <p className="text-[10px] uppercase tracking-widest text-green-400 mb-2 font-semibold">🧩 Clustering</p>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 4, right: 20, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey={xKey} name={xKey} tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <YAxis dataKey={yKey} name={yKey} tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Scatter data={chartData} shape={(props: {cx?: number; cy?: number; payload?: Record<string, unknown>}) => {
              const cluster = Number(props.payload?._cluster_id ?? 0);
              return (
                <circle
                  cx={props.cx}
                  cy={props.cy}
                  r={5}
                  fill={CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]}
                  opacity={0.75}
                />
              );
            }} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Trend → Line Chart
  if ((intent === "trend" || dateKey) && numericKeys.length > 0) {
    const xKey = dateKey || keys[0];
    return (
      <div className="w-full h-52">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: 20, bottom: 4, left: 0 }}>
            <defs>
              {numericKeys.slice(0, 3).map((k, i) => (
                <linearGradient key={k} id={`grad${i}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS[i]} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS[i]} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey={xKey} tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }} />
            {numericKeys.slice(0, 3).map((k, i) => (
              <Line key={k} dataKey={k} stroke={COLORS[i]} strokeWidth={2} dot={false}
                activeDot={{ r: 4, stroke: "#fff", strokeWidth: 1 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Top-N / Aggregation → Bar Chart
  if ((intent === "top_n" || intent === "aggregation") && numericKeys.length > 0 && categoryKey) {
    return (
      <div className="w-full h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData.slice(0, 15)} layout="vertical" margin={{ top: 4, right: 20, bottom: 4, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
            <XAxis type="number" tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <YAxis type="category" dataKey={categoryKey} tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} width={80} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey={numericKeys[0]} radius={[0, 4, 4, 0]}>
              {chartData.slice(0, 15).map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Generic fallback → simple bar
  if (numericKeys.length > 0) {
    const xKey = categoryKey || dateKey || keys[0];
    return (
      <div className="w-full h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData.slice(0, 20)} margin={{ top: 4, right: 20, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey={xKey} tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip content={<CustomTooltip />} />
            {numericKeys.slice(0, 2).map((k, i) => (
              <Bar key={k} dataKey={k} fill={COLORS[i]} radius={[4, 4, 0, 0]} fillOpacity={0.85} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return null;
}
