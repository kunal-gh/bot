"use client";

// src/components/DataTable.tsx
import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { formatNumber } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface DataTableProps {
  data: Record<string, unknown>[];
  pageSize?: number;
}

export function DataTable({ data, pageSize = 8 }: DataTableProps) {
  const [page, setPage] = useState(0);
  if (!data || data.length === 0) return null;

  const columns = Object.keys(data[0]);
  const totalPages = Math.ceil(data.length / pageSize);
  const rows = data.slice(page * pageSize, (page + 1) * pageSize);

  const formatCell = (val: unknown, col: string): string => {
    if (val === null || val === undefined) return "—";
    if (col === "_is_anomaly" || col === "_is_forecast") {
      return val ? "✓" : "";
    }
    if (col === "_cluster_id") return `Cluster ${val}`;
    if (typeof val === "number") return formatNumber(val);
    if (typeof val === "boolean") return val ? "Yes" : "No";
    return String(val);
  };

  const getCellStyle = (val: unknown, col: string): string => {
    if (col === "_is_anomaly" && val) return "text-amber-400 font-bold";
    if (col === "_is_forecast" && val) return "text-cyan-400";
    if (col === "_cluster_id") {
      const clusterColors = ["text-violet-400", "text-cyan-400", "text-green-400", "text-amber-400", "text-red-400"];
      return clusterColors[Number(val) % clusterColors.length];
    }
    return "text-slate-300";
  };

  const getColumnHeader = (col: string) => {
    if (col === "_is_anomaly") return "⚠ Anomaly";
    if (col === "_is_forecast") return "🔮 Forecast";
    if (col === "_cluster_id") return "🧩 Cluster";
    return col.replace(/_/g, " ");
  };

  return (
    <div className="overflow-hidden rounded-xl border border-white/5">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/5">
              {columns.map(col => (
                <th
                  key={col}
                  className="px-4 py-2.5 text-left font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap bg-white/[0.02]"
                >
                  {getColumnHeader(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className={cn(
                  "border-b border-white/5 transition-colors hover:bg-white/[0.03]",
                  row._is_anomaly ? "bg-amber-500/5" : "",
                  row._is_forecast ? "bg-cyan-500/5" : "",
                )}
              >
                {columns.map(col => (
                  <td
                    key={col}
                    className={cn("px-4 py-2 whitespace-nowrap font-mono", getCellStyle(row[col], col))}
                  >
                    {formatCell(row[col], col)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-2 border-t border-white/5 bg-white/[0.01]">
          <span className="text-[10px] text-slate-600">
            {data.length} rows · page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-1 rounded-lg hover:bg-white/10 disabled:opacity-30 transition-colors"
            >
              <ChevronLeft size={13} className="text-slate-400" />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="p-1 rounded-lg hover:bg-white/10 disabled:opacity-30 transition-colors"
            >
              <ChevronRight size={13} className="text-slate-400" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
