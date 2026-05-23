"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Database, ChevronDown, ChevronRight, Zap,
  RefreshCw, Link, Key, Calendar, BarChart2,
  Tag, Circle, Loader2,
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
    <aside className="flex flex-col h-full gap-6 overflow-hidden select-none">
      {/* Premium Spacious Header */}
      <div className="flex-shrink-0 px-2 pb-5 border-b border-white/5">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 flex items-center justify-center rounded-xl bg-zinc-900 border border-white/10 shadow-lg">
            <Database size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-black tracking-tighter text-white leading-none">BOT</h1>
            <p className="text-[9px] text-zinc-500 font-bold tracking-widest uppercase mt-0.5">Control Panel</p>
          </div>
        </div>
      </div>

      {/* Upload Workbook Block (Larger and spacious) */}
      <div className="flex-shrink-0 px-1">
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
          className="w-full rounded-xl p-4 flex flex-col items-center justify-center gap-3 transition-all duration-300 bg-zinc-900 border border-white/10 hover:border-white/20 disabled:opacity-50 cursor-pointer shadow-lg group text-center min-h-[96px]"
        >
          {uploading ? (
            <Loader2 size={20} className="text-zinc-400 animate-spin" />
          ) : (
            <Upload size={20} className="text-zinc-500 group-hover:text-white transition-colors duration-300" />
          )}
          <span className="text-xs font-bold text-zinc-300 group-hover:text-white transition-colors duration-300 uppercase tracking-wider">
            {uploading ? "Analyzing Workbook..." : "Upload Excel File"}
          </span>
        </button>

        {schema && (
          <button
            id="reload-btn"
            onClick={onReload}
            className="w-full mt-3 rounded-xl py-3 flex items-center justify-center gap-2 text-zinc-500 hover:text-white bg-zinc-950 border border-white/5 hover:border-white/10 transition-all duration-300 shadow-md cursor-pointer"
          >
            <RefreshCw size={12} />
            <span className="text-xs font-bold uppercase tracking-wider">Reload Dataset</span>
          </button>
        )}
      </div>

      {/* Schema Browser (Large and distinct) */}
      <div className="flex-1 min-h-0 overflow-y-auto chat-scroll space-y-1.5 pr-1">
        <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 mb-3 px-2">
          Segment Schema
        </p>
        {!schema ? (
          <div className="text-center py-10 border border-dashed border-white/5 rounded-2xl bg-zinc-950/20">
            <Database size={24} className="mx-auto mb-3 text-zinc-700 opacity-60" />
            <p className="text-xs font-semibold text-zinc-600">Pending workbook upload</p>
          </div>
        ) : (
          <div className="space-y-2">
            {schema.tables.map(table => (
              <div key={table.table_name} className="rounded-2xl overflow-hidden bg-zinc-900/10 border border-white/5 shadow-sm hover:border-white/10 transition-colors duration-300">
                <button
                  onClick={() => toggleTable(table.table_name)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors group cursor-pointer"
                >
                  {expandedTables.has(table.table_name)
                    ? <ChevronDown size={13} className="text-zinc-400 flex-shrink-0" />
                    : <ChevronRight size={13} className="text-zinc-500 flex-shrink-0" />
                  }
                  <Database size={13} className="text-zinc-400 flex-shrink-0" />
                  <span className="text-xs font-bold text-zinc-300 truncate group-hover:text-white flex-1 text-left">
                    {table.table_name}
                  </span>
                  <span className="text-[9px] font-mono text-zinc-500 bg-zinc-950 px-2 py-0.5 rounded-md border border-white/5">
                    {table.row_count}
                  </span>
                </button>

                <AnimatePresence>
                  {expandedTables.has(table.table_name) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <div className="ml-5 pl-3 border-l border-white/5 py-1.5 space-y-1 bg-zinc-950/30">
                        {table.columns.map(col => (
                          <div key={col.name} className="flex items-center gap-2.5 py-1 px-3 rounded-lg">
                            <span className="flex-shrink-0 opacity-80">{ROLE_ICON[col.role] || ROLE_ICON.unknown}</span>
                            <span className="text-[11px] text-zinc-400 truncate font-mono">{col.name}</span>
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
              <div className="mt-5 pt-5 border-t border-white/5">
                <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 mb-3 px-2">
                  Relationships
                </p>
                <div className="space-y-1.5">
                  {schema.relationships.slice(0, 4).map((rel, i) => (
                    <div key={i} className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl border border-white/5 bg-zinc-900/10 text-[10px] font-mono text-zinc-400">
                      <span className="truncate text-zinc-300 font-bold">{rel.left_table}</span>
                      <Link size={10} className="text-zinc-600 flex-shrink-0" />
                      <span className="truncate text-zinc-300 font-bold">{rel.right_table}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
