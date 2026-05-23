"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Bot, User, ChevronDown, ChevronRight, Code2,
  Table2, Info, Wrench, Brain,
} from "lucide-react";
import { ChatResponse } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { LoadingDots } from "@/components/ui/LoadingDots";
import { ResultChart } from "@/components/ResultChart";
import { DataTable } from "@/components/DataTable";
import { cn } from "@/lib/utils";

export interface Message {
  id: string;
  role: "user" | "bot";
  content: string;
  data?: ChatResponse;
  isLoading?: boolean;
  timestamp: Date;
}

function MLInsightBanner({ intent, data }: { intent: string; data: Record<string, unknown>[] }) {
  if (intent === "anomaly_detection" || intent === "anomaly_explain") {
    const anomalies = data.filter(r => r._is_anomaly);
    if (anomalies.length === 0) return null;
    return (
      <div className="flex items-start gap-3 rounded-xl border border-rose-500/10 bg-rose-950/5 px-4 py-3 select-none">
        <span className="text-rose-400 text-sm flex-shrink-0">⚠️</span>
        <div>
          <p className="text-xs font-semibold text-rose-300">
            {anomalies.length} anomaly detected
          </p>
          <p className="text-[11px] text-rose-400/70 mt-0.5 leading-relaxed">
            Outliers identified by Isolation Forest model (5% contamination rate threshold).
          </p>
        </div>
      </div>
    );
  }
  if (intent === "forecast") {
    const forecasted = data.filter(r => r._is_forecast);
    return (
      <div className="flex items-start gap-3 rounded-xl border border-zinc-500/10 bg-zinc-950/30 px-4 py-3 select-none">
        <span className="text-zinc-400 text-sm flex-shrink-0">🔮</span>
        <div>
          <p className="text-xs font-semibold text-zinc-300">
            {forecasted.length}-Period Forecast Generated
          </p>
          <p className="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">
            Computed using Simple Exponential Smoothing model.
          </p>
        </div>
      </div>
    );
  }
  if (intent === "cluster") {
    const clusters = new Set(data.map(r => r._cluster_id));
    return (
      <div className="flex items-start gap-3 rounded-xl border border-emerald-500/10 bg-emerald-950/5 px-4 py-3 select-none">
        <span className="text-emerald-400 text-sm flex-shrink-0">🧩</span>
        <div>
          <p className="text-xs font-semibold text-emerald-300">
            {clusters.size} dynamic segments identified
          </p>
          <p className="text-[11px] text-emerald-400/70 mt-0.5 leading-relaxed">
            Multi-dimensional K-Means clustering run on active numeric variables.
          </p>
        </div>
      </div>
    );
  }
  return null;
}

interface ExpandableSectionProps {
  title: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function ExpandableSection({ title, children, defaultOpen = false }: ExpandableSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-white/5 rounded-xl overflow-hidden bg-zinc-950/10">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-white/[0.02] transition-colors select-none"
      >
        {open
          ? <ChevronDown size={12} className="text-zinc-500" />
          : <ChevronRight size={12} className="text-zinc-500" />
        }
        {title}
      </button>
      {open && <div className="px-4 pb-4 pt-1">{children}</div>}
    </div>
  );
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "flex gap-4 w-full",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div className={cn(
        "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center select-none",
        isUser
          ? "bg-zinc-100 text-zinc-950 font-bold"
          : "bg-zinc-900 border border-white/10 text-white"
      )}>
        {isUser
          ? <User size={14} />
          : <Bot size={14} className="text-zinc-300" />
        }
      </div>

      {/* Content */}
      <div className={cn(
        "flex flex-col gap-2 max-w-[82%]",
        isUser ? "items-end" : "items-start"
      )}>
        {/* Main bubble */}
        <div className={cn(
          "rounded-xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-zinc-900 border border-white/10 text-zinc-100"
            : "bg-zinc-900/30 border border-white/5 text-zinc-300"
        )}>
          {message.isLoading ? (
            <LoadingDots />
          ) : (
            <p className="whitespace-pre-wrap font-sans">{message.content}</p>
          )}
        </div>

        {/* Bot enrichments */}
        {!isUser && message.data && !message.isLoading && (
          <div className="w-full space-y-2.5">
            {/* Badges */}
            <div className="flex flex-wrap gap-1.5 px-1 select-none">
              {message.data.query_complexity && (
                <Badge variant="purple">
                  <Brain size={9} />
                  {message.data.query_complexity}
                </Badge>
              )}
              {message.data.tables_used?.map(t => (
                <Badge key={t} variant="cyan">{t}</Badge>
              ))}
              {message.data.was_repaired && (
                <Badge variant="amber">
                  <Wrench size={9} />
                  Auto-repaired
                </Badge>
              )}
            </div>

            {/* ML Insight Banner */}
            {message.data.result_preview && message.data.result_preview.length > 0 && (
              <MLInsightBanner
                intent={
                  message.data.query_complexity?.toLowerCase().includes("forecast") ? "forecast"
                  : message.data.query_complexity?.toLowerCase().includes("anomaly") ? "anomaly_detection"
                  : message.data.query_complexity?.toLowerCase().includes("cluster") ? "cluster"
                  : ""
                }
                data={message.data.result_preview}
              />
            )}

            {/* Chart */}
            {message.data.result_preview && message.data.result_preview.length > 0 && (
              <div className="bg-zinc-900/20 border border-white/5 rounded-xl p-4">
                <ResultChart
                  data={message.data.result_preview}
                  intent={
                    message.data.query_complexity?.toLowerCase().includes("forecast") ? "forecast"
                    : message.data.query_complexity?.toLowerCase().includes("top") ? "top_n"
                    : message.data.query_complexity?.toLowerCase().includes("trend") ? "trend"
                    : message.data.query_complexity?.toLowerCase().includes("aggregat") ? "aggregation"
                    : ""
                  }
                />
              </div>
            )}

            {/* Data Table */}
            {message.data.result_preview && message.data.result_preview.length > 0 && (
              <ExpandableSection
                title={
                  <span className="flex items-center gap-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                    <Table2 size={12} />
                    Data View
                    <span className="ml-auto text-zinc-600 font-mono text-[9px] lowercase">
                      {message.data.result_preview.length} rows
                    </span>
                  </span>
                }
                defaultOpen={message.data.result_preview.length <= 8}
              >
                <DataTable data={message.data.result_preview} />
              </ExpandableSection>
            )}

            {/* SQL */}
            {message.data.sql && (
              <ExpandableSection
                title={
                  <span className="flex items-center gap-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                    <Code2 size={12} />
                    SQL Pipeline
                  </span>
                }
              >
                <pre className="bg-zinc-950/60 rounded-xl p-3.5 text-xs text-zinc-400 overflow-x-auto font-mono leading-relaxed border border-white/5 select-text">
                  {message.data.sql}
                </pre>
              </ExpandableSection>
            )}

            {/* Explanation */}
            {message.data.explanation && (
              <ExpandableSection
                title={
                  <span className="flex items-center gap-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                    <Info size={12} />
                    Explanation
                  </span>
                }
              >
                <p className="text-xs text-zinc-400 leading-relaxed font-sans select-text">{message.data.explanation}</p>
              </ExpandableSection>
            )}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[9px] font-semibold text-zinc-600 px-1 select-none uppercase tracking-wider">
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </motion.div>
  );
}
