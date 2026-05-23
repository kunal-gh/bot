"use client";

// src/components/ChatMessage.tsx
import { useState } from "react";
import { motion } from "framer-motion";
import {
  Bot, User, ChevronDown, ChevronRight, Code2,
  Table2, Info, Wrench, Sparkles, BarChart3, Brain,
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

const INTENT_META: Record<string, { label: string; color: "purple" | "cyan" | "green" | "amber" | "red" }> = {
  forecast:         { label: "Forecast",   color: "cyan" },
  anomaly_explain:  { label: "Anomaly",    color: "amber" },
  anomaly_detection:{ label: "Anomaly",    color: "amber" },
  cluster:          { label: "Cluster",    color: "green" },
  top_n:            { label: "Top-N",      color: "purple" },
  trend:            { label: "Trend",      color: "green" },
  aggregation:      { label: "Aggregate",  color: "purple" },
  comparison:       { label: "Compare",    color: "amber" },
  lookup:           { label: "Lookup",     color: "cyan" },
  join_based:       { label: "Join",       color: "purple" },
  derived_metric:   { label: "Metric",     color: "green" },
};

function MLInsightBanner({ intent, data }: { intent: string; data: Record<string, unknown>[] }) {
  if (intent === "anomaly_detection" || intent === "anomaly_explain") {
    const anomalies = data.filter(r => r._is_anomaly);
    if (anomalies.length === 0) return null;
    return (
      <div className="flex items-start gap-2.5 rounded-xl border border-amber-400/20 bg-amber-400/5 px-4 py-3">
        <span className="text-amber-400 text-base flex-shrink-0">⚠️</span>
        <div>
          <p className="text-sm font-semibold text-amber-300">
            {anomalies.length} anomal{anomalies.length > 1 ? "ies" : "y"} detected
          </p>
          <p className="text-xs text-amber-400/70 mt-0.5">
            Highlighted rows contain outliers identified by Isolation Forest (5% contamination rate).
          </p>
        </div>
      </div>
    );
  }
  if (intent === "forecast") {
    const forecasted = data.filter(r => r._is_forecast);
    return (
      <div className="flex items-start gap-2.5 rounded-xl border border-cyan-400/20 bg-cyan-400/5 px-4 py-3">
        <span className="text-cyan-400 text-base flex-shrink-0">🔮</span>
        <div>
          <p className="text-sm font-semibold text-cyan-300">
            {forecasted.length}-period forecast generated
          </p>
          <p className="text-xs text-cyan-400/70 mt-0.5">
            Using Simple Exponential Smoothing. Forecast values shown in cyan.
          </p>
        </div>
      </div>
    );
  }
  if (intent === "cluster") {
    const clusters = new Set(data.map(r => r._cluster_id));
    return (
      <div className="flex items-start gap-2.5 rounded-xl border border-green-400/20 bg-green-400/5 px-4 py-3">
        <span className="text-green-400 text-base flex-shrink-0">🧩</span>
        <div>
          <p className="text-sm font-semibold text-green-300">
            {clusters.size} segments identified
          </p>
          <p className="text-xs text-green-400/70 mt-0.5">
            K-Means clustering on numeric features. Segments color-coded in chart.
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
    <div className="border border-white/5 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-white/[0.03] transition-colors"
      >
        {open
          ? <ChevronDown size={13} className="text-slate-600" />
          : <ChevronRight size={13} className="text-slate-600" />
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
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn(
        "flex gap-3",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div className={cn(
        "flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center",
        isUser
          ? "bg-gradient-to-br from-violet-500 to-cyan-500"
          : "bg-gradient-to-br from-slate-700 to-slate-800 border border-white/10"
      )}>
        {isUser
          ? <User size={15} className="text-white" />
          : <Bot size={15} className="text-violet-300" />
        }
      </div>

      {/* Content */}
      <div className={cn(
        "flex flex-col gap-2 max-w-[85%]",
        isUser ? "items-end" : "items-start"
      )}>
        {/* Main bubble */}
        <div className={cn(
          "rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-gradient-to-br from-violet-600/40 to-cyan-600/20 border border-violet-500/30 text-white"
            : "glass border border-white/5 text-slate-200"
        )}>
          {message.isLoading ? (
            <LoadingDots />
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* Bot enrichments */}
        {!isUser && message.data && !message.isLoading && (
          <div className="w-full space-y-2.5">
            {/* Badges */}
            <div className="flex flex-wrap gap-1.5 px-1">
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
                intent={/* Extract intent from query_complexity */
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
              <div className="glass rounded-2xl p-4 border border-white/5">
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
                  <span className="flex items-center gap-2 text-xs text-slate-500">
                    <Table2 size={13} />
                    Data Table
                    <span className="ml-auto text-slate-700 text-[10px]">
                      {message.data.result_preview.length} rows
                    </span>
                  </span>
                }
                defaultOpen={message.data.result_preview.length <= 10}
              >
                <DataTable data={message.data.result_preview} />
              </ExpandableSection>
            )}

            {/* SQL */}
            {message.data.sql && (
              <ExpandableSection
                title={
                  <span className="flex items-center gap-2 text-xs text-slate-500">
                    <Code2 size={13} />
                    SQL Query
                  </span>
                }
              >
                <pre className="bg-black/40 rounded-xl p-3 text-xs text-green-300 overflow-x-auto font-mono leading-relaxed border border-white/5">
                  {message.data.sql}
                </pre>
              </ExpandableSection>
            )}

            {/* Explanation */}
            {message.data.explanation && (
              <ExpandableSection
                title={
                  <span className="flex items-center gap-2 text-xs text-slate-500">
                    <Info size={13} />
                    Explanation
                  </span>
                }
              >
                <p className="text-xs text-slate-400 leading-relaxed">{message.data.explanation}</p>
              </ExpandableSection>
            )}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[9px] text-slate-700 px-1">
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </motion.div>
  );
}
