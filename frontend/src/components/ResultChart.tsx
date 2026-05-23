"use client";

import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from "recharts";
import { formatNumber } from "@/lib/utils";

interface ResultChartProps {
  data: Record<string, unknown>[];
  intent: string;
}

const COLORS = ["#d4d4d8", "#a1a1aa", "#71717a", "#52525b", "#3f3f46"];
const ANOMALY_COLOR = "#f87171"; // Premium clean rust-rose warning color
const FORECAST_COLOR = "#60a5fa"; // Premium clean soft blue for forecast projections
const CLUSTER_COLORS = ["#e4e4e7", "#a1a1aa", "#71717a", "#52525b", "#3f3f46"];

const CustomTooltip = ({ active, payload, label }: {active?: boolean; payload?: Array<{name: string; value: unknown; color: string; payload?: Record<string, unknown>}>; label?: string}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-white/10 rounded-xl p-3.5 shadow-2xl text-xs min-w-[150px] select-none">
      {label && <p className="text-zinc-400 mb-2 font-bold tracking-wide">{label}</p>}
      {payload.map((p, i) => {
        const isAnomaly = Boolean(p.payload?._is_anomaly);
        const isForecast = Boolean(p.payload?._is_forecast);
        return (
          <div key={i} className="flex flex-col gap-1 mb-1 border-b border-white/5 pb-1 last:border-0 last:pb-0">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: isAnomaly ? ANOMALY_COLOR : isForecast ? FORECAST_COLOR : p.color }} />
              <span className="text-zinc-400 font-semibold">{p.name}:</span>
              <span className="text-white font-black ml-auto">
                {typeof p.value === "number" ? formatNumber(p.value) : String(p.value)}
              </span>
            </div>
            {isAnomaly && (
              <span className="text-[9px] font-bold text-rose-400 uppercase tracking-widest pl-3.5">⚠️ Outlier Detected</span>
            )}
            {isForecast && (
              <span className="text-[9px] font-bold text-blue-400 uppercase tracking-widest pl-3.5">🔮 Projected Period</span>
            )}
          </div>
        );
      })}
    </div>
  );
};

export function ResultChart({ data, intent }: ResultChartProps) {
  if (!data || data.length === 0) return null;

  const keys = Object.keys(data[0]);
  
  // Isolate Date keys reliably
  const dateKey = keys.find(k =>
    ["date", "day", "month", "year", "time", "created_at", "ordered_at", "period"].some(d => k.toLowerCase().includes(d))
  );

  // Clean numeric metrics (EXCLUDING dates and ML columns!)
  const numericKeys = keys.filter(k => {
    const lowerKey = k.toLowerCase();
    if (["_is_anomaly", "_is_forecast", "_cluster_id", "id"].includes(lowerKey)) return false;
    if (dateKey && k === dateKey) return false;
    const val = data.find(r => r[k] !== null)?.[k];
    return typeof val === "number" || (!isNaN(Number(val)) && String(val).trim() !== "");
  });

  const categoryKey = keys.find(k => k !== dateKey && !numericKeys.includes(k) && !["_is_anomaly", "_is_forecast", "_cluster_id"].includes(k));

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

  // 1. Forecast Mode -> Line Chart with blue projections
  if (intent === "forecast" || isForecastData) {
    const xKey = dateKey || keys[0];
    const yKey = numericKeys[0];
    if (!yKey) return null;

    return (
      <div className="w-full h-64 select-none">
        <p className="text-[10px] uppercase tracking-widest text-zinc-400 mb-3.5 font-bold">
          🔮 Forecast Projection — {chartData.filter(r => r._is_forecast).length} Periods Projected
        </p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey={xKey} tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Line
              dataKey={yKey}
              stroke="#fafafa"
              strokeWidth={2}
              dot={(props: {payload?: Record<string, unknown>; cx?: number; cy?: number}) => {
                if (props.payload?._is_forecast) {
                  return (
                    <circle key={Math.random()} cx={props.cx} cy={props.cy} r={3} fill={FORECAST_COLOR} stroke="none" />
                  );
                }
                return <span key={Math.random()} />;
              }}
              activeDot={{ r: 4, fill: "#ffffff", stroke: "#000", strokeWidth: 1 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // 2. Anomaly Mode -> Smart Highlighted Bar Chart (if Date is present) or Scatter Chart (if multiple numeric variables)
  if (isAnomalyData && numericKeys.length > 0) {
    const yKey = numericKeys[0];
    
    // Time-Series Anomaly (Most common & extremely readable!)
    if (dateKey) {
      return (
        <div className="w-full h-64 select-none">
          <p className="text-[10px] uppercase tracking-widest text-rose-400 mb-3.5 font-bold">
            ⚠️ Anomaly Detection — {chartData.filter(r => r._is_anomaly).length} Outliers Found
          </p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis dataKey={dateKey} tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry._is_anomaly ? ANOMALY_COLOR : "#3f3f46"}
                    fillOpacity={entry._is_anomaly ? 1 : 0.4}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    }

    // Multidimensional Anomaly Scatter Chart (if 2+ numeric keys)
    if (numericKeys.length >= 2) {
      const xKey = numericKeys[0];
      const yKey = numericKeys[1];
      return (
        <div className="w-full h-64 select-none">
          <p className="text-[10px] uppercase tracking-widest text-rose-400 mb-3.5 font-bold">🔍 Multidimensional Outliers</p>
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
              <XAxis dataKey={xKey} name={xKey} tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
              <YAxis dataKey={yKey} name={yKey} tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
              <Tooltip content={<CustomTooltip />} />
              <Scatter data={chartData} shape={(props: {cx?: number; cy?: number; payload?: Record<string, unknown>}) => {
                const isAnomaly = props.payload?._is_anomaly;
                return (
                  <circle
                    cx={props.cx}
                    cy={props.cy}
                    r={isAnomaly ? 6 : 3.5}
                    fill={isAnomaly ? ANOMALY_COLOR : "#a1a1aa"}
                    opacity={isAnomaly ? 1 : 0.4}
                  />
                );
              }} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      );
    }
  }

  // 3. Cluster Mode -> Scatter/Bar with cluster coloring
  if (isClusterData && numericKeys.length > 0) {
    const yKey = numericKeys[0];
    
    // Time Series clusters (if dateKey is present)
    if (dateKey) {
      return (
        <div className="w-full h-64 select-none">
          <p className="text-[10px] uppercase tracking-widest text-zinc-400 mb-3.5 font-bold">🧩 Dynamic Segment Distribution</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis dataKey={dateKey} tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => {
                  const cluster = Number(entry._cluster_id ?? 0);
                  return (
                    <Cell
                      key={`cell-${index}`}
                      fill={CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]}
                      fillOpacity={0.8}
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    }
  }

  // 4. Trend Mode -> Line Chart
  if ((intent === "trend" || dateKey) && numericKeys.length > 0) {
    const xKey = dateKey || keys[0];
    return (
      <div className="w-full h-60 select-none">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey={xKey} tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "10px", color: "#a1a1aa" }} />
            {numericKeys.slice(0, 3).map((k, i) => (
              <Line key={k} dataKey={k} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false}
                activeDot={{ r: 4, stroke: "#fff", strokeWidth: 1 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // 5. Top-N / Aggregation Mode -> Vertical Bar Chart
  if ((intent === "top_n" || intent === "aggregation") && numericKeys.length > 0 && categoryKey) {
    return (
      <div className="w-full h-60 select-none">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData.slice(0, 15)} layout="vertical" margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" horizontal={false} />
            <XAxis type="number" tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <YAxis type="category" dataKey={categoryKey} tick={{ fill: "#a1a1aa", fontSize: 9 }} axisLine={false} tickLine={false} width={80} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey={numericKeys[0]} radius={[0, 4, 4, 0]}>
              {chartData.slice(0, 15).map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // 6. Generic Fallback -> Clean standard Bar Chart
  if (numericKeys.length > 0) {
    const xKey = categoryKey || dateKey || keys[0];
    return (
      <div className="w-full h-60 select-none">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData.slice(0, 20)} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey={xKey} tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#52525b", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip content={<CustomTooltip />} />
            {numericKeys.slice(0, 2).map((k, i) => (
              <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} fillOpacity={0.8} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return null;
}
