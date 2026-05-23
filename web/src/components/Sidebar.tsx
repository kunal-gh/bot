"use client";

// src/components/Sidebar.tsx
import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Database, ChevronDown, ChevronRight, Zap,
  RefreshCw, Activity, Link, Key, Calendar, BarChart2,
  Tag, Circle, Loader2, CheckCircle, XCircle,
} from "lucide-react";
import { TableMeta, RelationshipMeta } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";

interface SidebarProps {
  schema: { tables: TableMeta[]; relationships: RelationshipMeta[] } | null;
  health: { status: string; tables_loaded: number; duckdb_connected: boolean } | null;
  onUpload: (file: File) => void;
  onReload: () => void;
  onSampleQuery: (query: string) => void;
  uploading: boolean;
  sampleQueries: string[];
}

const ROLE_ICON: Record<string, React.ReactNode> = {
  primary_key: <Key size={11} className="text-yellow-400" />,
  foreign_key: <Link size={11} className="text-blue-400" />,
  date: <Calendar size={11} className="text-cyan-400" />,
  measure: <BarChart2 size={11} className="text-violet-400" />,
  dimension: <Tag size={11} className="text-green-400" />,
  unknown: <Circle size={11} className="text-slate-500" />,
};

export function Sidebar({
  schema, health, onUpload, onReload, onSampleQuery,
  uploading, sampleQueries,
}: SidebarProps) {
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const fileRef = useRef<HTMLInputElement>(null);

  const toggleTable = (name: string) => {
    setExpandedTables(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <aside className="flex flex-col h-full gap-4 overflow-hidden">
      {/* Logo Header */}
      <div className="flex-shrink-0 px-1">
        <div className="flex items-center gap-3 mb-1">
          <div className="relative w-9 h-9 flex items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 glow-accent">
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold gradient-text tracking-tight">BOT</h1>
            <p className="text-[10px] text-slate-500 leading-none">AI Analytics Agent</p>
          </div>
        </div>
      </div>

      {/* Upload */}
      <div className="flex-shrink-0">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2 px-1">
          Data Source
        </p>
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xls"
          className="hidden"
          onChange={e => {
            const f = e.target.files?.[0];
            if (f) { onUpload(f); e.target.value = ""; }
          }}
        />
        <button
          id="upload-btn"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="w-full gradient-border rounded-xl p-3 flex items-center gap-3 transition-all duration-200 hover:bg-violet-500/10 disabled:opacity-50 cursor-pointer group"
          style={{ background: "var(--bg-card)" }}
        >
          {uploading ? (
            <Loader2 size={16} className="text-violet-400 animate-spin" />
          ) : (
            <Upload size={16} className="text-violet-400 group-hover:text-violet-300 transition-colors" />
          )}
          <span className="text-sm font-medium text-slate-300 group-hover:text-white transition-colors">
            {uploading ? "Loading…" : "Upload Excel File"}
          </span>
        </button>

        {schema && (
          <button
            id="reload-btn"
            onClick={onReload}
            className="w-full mt-2 rounded-xl p-2.5 flex items-center gap-2.5 text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all duration-200"
          >
            <RefreshCw size={14} />
            <span className="text-xs">Reload Dataset</span>
          </button>
        )}
      </div>

      {/* Schema Browser */}
      <div className="flex-1 min-h-0 overflow-y-auto chat-scroll space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2 px-1">
          Schema
        </p>
        {!schema ? (
          <div className="text-center py-6 text-slate-600">
            <Database size={24} className="mx-auto mb-2 opacity-40" />
            <p className="text-xs">Upload a file to view schema</p>
          </div>
        ) : (
          <>
            {schema.tables.map(table => (
              <div key={table.table_name} className="rounded-xl overflow-hidden">
                <button
                  onClick={() => toggleTable(table.table_name)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-white/5 transition-colors rounded-xl group"
                >
                  {expandedTables.has(table.table_name)
                    ? <ChevronDown size={13} className="text-violet-400 flex-shrink-0" />
                    : <ChevronRight size={13} className="text-slate-600 flex-shrink-0" />
                  }
                  <Database size={13} className="text-violet-400 flex-shrink-0" />
                  <span className="text-xs font-medium text-slate-300 truncate group-hover:text-white flex-1 text-left">
                    {table.table_name}
                  </span>
                  <span className="text-[9px] text-slate-600 flex-shrink-0">
                    {table.row_count.toLocaleString()}r
                  </span>
                </button>

                <AnimatePresence>
                  {expandedTables.has(table.table_name) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="ml-4 pl-3 border-l border-white/5 py-1 space-y-0.5">
                        {table.columns.map(col => (
                          <div key={col.name} className="flex items-center gap-1.5 py-0.5 px-2 rounded-lg hover:bg-white/5">
                            <span className="flex-shrink-0">{ROLE_ICON[col.role] || ROLE_ICON.unknown}</span>
                            <span className="text-[11px] text-slate-400 truncate font-mono">{col.name}</span>
                            <span className="text-[9px] text-slate-600 ml-auto flex-shrink-0">{col.sql_type.split("(")[0]}</span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}

            {schema.relationships.length > 0 && (
              <div className="mt-3">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600 mb-1.5 px-1">
                  Relationships
                </p>
                {schema.relationships.slice(0, 6).map((rel, i) => (
                  <div key={i} className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-white/5 text-[10px]">
                    <span className="text-violet-400 font-mono truncate">{rel.left_table}</span>
                    <Link size={9} className="text-slate-600 flex-shrink-0" />
                    <span className="text-cyan-400 font-mono truncate">{rel.right_table}</span>
                    <span className="ml-auto text-slate-600 flex-shrink-0">
                      {(rel.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Sample Queries */}
      <div className="flex-shrink-0 space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2 px-1">
          Try These
        </p>
        {sampleQueries.slice(0, 5).map((q, i) => (
          <button
            key={i}
            id={`sample-query-${i}`}
            onClick={() => onSampleQuery(q)}
            className="w-full text-left px-3 py-2 rounded-lg text-[11px] text-slate-500 hover:text-slate-200 hover:bg-white/5 transition-all duration-150 truncate border border-transparent hover:border-white/10"
          >
            💬 {q}
          </button>
        ))}
      </div>

      {/* Health */}
      <div className="flex-shrink-0 pt-2 border-t border-white/5">
        <div className="flex items-center gap-2 px-1">
          {health?.duckdb_connected ? (
            <CheckCircle size={12} className="text-green-400" />
          ) : (
            <XCircle size={12} className="text-red-400" />
          )}
          <span className="text-[10px] text-slate-600">
            {health?.duckdb_connected ? "Backend connected" : "Backend offline"}
          </span>
          {health && health.tables_loaded > 0 && (
            <span className="ml-auto text-[10px] text-violet-400">
              {health.tables_loaded} table{health.tables_loaded > 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}
