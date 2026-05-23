"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Database, ChevronDown, ChevronRight, Zap,
  RefreshCw, Link, Key, Calendar, BarChart2,
  Tag, Circle, Loader2, CheckCircle, XCircle,
} from "lucide-react";
import { TableMeta, RelationshipMeta } from "@/lib/api";

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
  primary_key: <Key size={11} className="text-zinc-400" />,
  foreign_key: <Link size={11} className="text-zinc-500" />,
  date: <Calendar size={11} className="text-zinc-400" />,
  measure: <BarChart2 size={11} className="text-zinc-400" />,
  dimension: <Tag size={11} className="text-zinc-500" />,
  unknown: <Circle size={11} className="text-zinc-600" />,
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
    <aside className="flex flex-col h-full gap-5 overflow-hidden select-none">
      {/* Logo Header */}
      <div className="flex-shrink-0 px-1 border-b border-white/5 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 flex items-center justify-center rounded-lg bg-zinc-900 border border-white/10">
            <Zap size={15} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold tracking-tight text-white leading-tight">BOT</h1>
            <p className="text-[9px] text-zinc-500 font-medium tracking-wide leading-none uppercase">Beyond Ordinary Tables</p>
          </div>
        </div>
      </div>

      {/* Upload */}
      <div className="flex-shrink-0">
        <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 mb-2.5 px-1">
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
          className="w-full rounded-xl p-3 flex items-center gap-3 transition-all duration-200 bg-zinc-900 border border-white/10 hover:border-white/20 disabled:opacity-50 cursor-pointer group"
        >
          {uploading ? (
            <Loader2 size={15} className="text-zinc-400 animate-spin" />
          ) : (
            <Upload size={15} className="text-zinc-400 group-hover:text-zinc-200 transition-colors" />
          )}
          <span className="text-xs font-semibold text-zinc-300 group-hover:text-white transition-colors">
            {uploading ? "Analyzing workbook…" : "Upload Excel Workbook"}
          </span>
        </button>

        {schema && (
          <button
            id="reload-btn"
            onClick={onReload}
            className="w-full mt-2 rounded-xl p-2 flex items-center justify-center gap-2 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/50 border border-transparent hover:border-white/5 transition-all duration-200"
          >
            <RefreshCw size={12} />
            <span className="text-[11px] font-medium">Reload Dataset</span>
          </button>
        )}
      </div>

      {/* Schema Browser */}
      <div className="flex-1 min-h-0 overflow-y-auto chat-scroll space-y-1 pr-1">
        <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 mb-2.5 px-1">
          Tables Loaded
        </p>
        {!schema ? (
          <div className="text-center py-8 border border-dashed border-white/5 rounded-xl">
            <Database size={20} className="mx-auto mb-2 text-zinc-600 opacity-60" />
            <p className="text-[11px] text-zinc-500">No schema loaded</p>
          </div>
        ) : (
          <div className="space-y-1">
            {schema.tables.map(table => (
              <div key={table.table_name} className="rounded-xl overflow-hidden bg-zinc-900/20 border border-white/5">
                <button
                  onClick={() => toggleTable(table.table_name)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/5 transition-colors group"
                >
                  {expandedTables.has(table.table_name)
                    ? <ChevronDown size={12} className="text-zinc-400 flex-shrink-0" />
                    : <ChevronRight size={12} className="text-zinc-500 flex-shrink-0" />
                  }
                  <Database size={12} className="text-zinc-400 flex-shrink-0" />
                  <span className="text-[11px] font-medium text-zinc-300 truncate group-hover:text-white flex-1 text-left">
                    {table.table_name}
                  </span>
                  <span className="text-[9px] font-mono text-zinc-500 flex-shrink-0">
                    {table.row_count}
                  </span>
                </button>

                <AnimatePresence>
                  {expandedTables.has(table.table_name) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <div className="ml-4 pl-3 border-l border-white/5 py-1 space-y-0.5 bg-zinc-950/40">
                        {table.columns.map(col => (
                          <div key={col.name} className="flex items-center gap-1.5 py-0.5 px-2 rounded-lg">
                            <span className="flex-shrink-0 opacity-80">{ROLE_ICON[col.role] || ROLE_ICON.unknown}</span>
                            <span className="text-[10px] text-zinc-400 truncate font-mono">{col.name}</span>
                            <span className="text-[9px] text-zinc-600 ml-auto flex-shrink-0 font-mono">{col.sql_type.split("(")[0]}</span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}

            {schema.relationships.length > 0 && (
              <div className="mt-4 pt-4 border-t border-white/5">
                <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 mb-2 px-1">
                  Relational Links
                </p>
                <div className="space-y-1">
                  {schema.relationships.slice(0, 5).map((rel, i) => (
                    <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/5 bg-zinc-900/10 text-[10px] font-mono text-zinc-400">
                      <span className="truncate text-zinc-300">{rel.left_table}</span>
                      <Link size={10} className="text-zinc-600 flex-shrink-0" />
                      <span className="truncate text-zinc-300">{rel.right_table}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Sample Queries */}
      <div className="flex-shrink-0 space-y-1.5 border-t border-white/5 pt-4">
        <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 mb-1 px-1">
          Explore Examples
        </p>
        {sampleQueries.slice(0, 4).map((q, i) => (
          <button
            key={i}
            id={`sample-query-${i}`}
            onClick={() => onSampleQuery(q)}
            className="w-full text-left px-3 py-2 rounded-xl text-[10px] text-zinc-400 hover:text-white bg-zinc-900/10 border border-white/5 hover:border-white/10 hover:bg-zinc-900/40 transition-all duration-150 truncate"
          >
            💬 {q}
          </button>
        ))}
      </div>

      {/* Health */}
      <div className="flex-shrink-0 pt-3 border-t border-white/5">
        <div className="flex items-center gap-2 px-1 text-[10px] text-zinc-500">
          {health?.duckdb_connected ? (
            <CheckCircle size={11} className="text-emerald-500" />
          ) : (
            <XCircle size={11} className="text-rose-400" />
          )}
          <span>
            {health?.duckdb_connected ? "Engine Ready" : "Disconnected"}
          </span>
          {health && health.tables_loaded > 0 && (
            <span className="ml-auto text-[9px] font-mono text-zinc-400">
              {health.tables_loaded} TBL
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}
