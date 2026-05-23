"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, SchemaResponse, HealthResponse } from "@/lib/api";
import { SAMPLE_QUERIES } from "@/lib/utils";
import { Sidebar } from "@/components/Sidebar";
import { ChatMessage, Message } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { WelcomeHero } from "@/components/WelcomeHero";
import { Menu, X, Check, AlertCircle, Info, ChevronRight } from "lucide-react";

let msgId = 0;
const newId = () => `msg-${++msgId}`;

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [notification, setNotification] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [statusHovered, setStatusHovered] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-dismiss notification
  useEffect(() => {
    if (!notification) return;
    const t = setTimeout(() => setNotification(null), 4000);
    return () => clearTimeout(t);
  }, [notification]);

  // Fetch health + schema on mount
  const refreshData = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
      if (h.tables_loaded > 0) {
        const s = await api.schema();
        setSchema(s);
      } else {
        setSchema(null);
      }
    } catch {
      setHealth(null);
      setSchema(null);
    }
  }, []);

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 10000);
    return () => clearInterval(interval);
  }, [refreshData]);

  // Upload handler
  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const result = await api.upload(file);
      setNotification({ type: "success", msg: result.message });
      const s = await api.schema();
      setSchema(s);
      const h = await api.health();
      setHealth(h);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setNotification({ type: "error", msg: message });
    } finally {
      setUploading(false);
    }
  };

  // Reload handler
  const handleReload = async () => {
    try {
      const result = await api.reload();
      setNotification({ type: "success", msg: result.message });
      const s = await api.schema();
      setSchema(s);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Reload failed";
      setNotification({ type: "error", msg: message });
    }
  };

  // Send message
  const handleSend = async (query: string) => {
    if (isLoading) return;

    // Add user message
    const userMsg: Message = {
      id: newId(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    // Add loading bot message
    const loadingMsg: Message = {
      id: newId(),
      role: "bot",
      content: "",
      isLoading: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setIsLoading(true);

    try {
      const data = await api.chat(query);
      setMessages(prev => [
        ...prev.filter(m => m.id !== loadingMsg.id),
        {
          id: newId(),
          role: "bot",
          content: data.error ? `⚠️ ${data.error}` : data.answer,
          data: data.error ? undefined : data,
          timestamp: new Date(),
        },
      ]);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Backend error";
      setMessages(prev => [
        ...prev.filter(m => m.id !== loadingMsg.id),
        {
          id: newId(),
          role: "bot",
          content: `⚠️ ${message}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const hasWorkbook = !!schema && schema.tables.length > 0;
  const isOnline = !!health?.duckdb_connected;

  return (
    <div className="relative flex h-screen overflow-hidden bg-zinc-950 text-zinc-100 font-sans">
      
      {/* ── Sidebar ── */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ x: -280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -280, opacity: 0 }}
            transition={{ type: "spring", damping: 30, stiffness: 220 }}
            className="relative z-20 w-64 flex-shrink-0 h-full bg-zinc-950 border-r border-white/5 p-5 flex flex-col"
          >
            <Sidebar
              schema={schema}
              health={health}
              onUpload={handleUpload}
              onReload={handleReload}
              onSampleQuery={handleSend}
              uploading={uploading}
              sampleQueries={SAMPLE_QUERIES}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Main Panel ── */}
      <div className="relative z-10 flex flex-col flex-1 min-w-0 overflow-hidden bg-zinc-950/60">
        
        {/* Top bar */}
        <header className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-white/5 bg-zinc-950/40 backdrop-blur-md select-none">
          <div className="flex items-center gap-4">
            <button
              id="sidebar-toggle"
              onClick={() => setSidebarOpen(v => !v)}
              className="w-8 h-8 rounded-lg flex items-center justify-center bg-zinc-900 border border-white/5 hover:border-white/10 transition-colors text-zinc-400 hover:text-white cursor-pointer"
            >
              {sidebarOpen ? <X size={14} /> : <Menu size={14} />}
            </button>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-sm tracking-widest text-zinc-100 uppercase font-sans">Beyond Ordinary Tables</span>
                <span className="text-[9px] font-bold text-zinc-600 tracking-wider">V1.4</span>
              </div>
              <p className="text-[10px] text-zinc-500 font-medium">
                {hasWorkbook
                  ? `${schema.tables.length} Active Segment${schema.tables.length > 1 ? "s" : ""} Loaded`
                  : "Upload a structured dataset to start"
                }
              </p>
            </div>
          </div>

          {/* Premium Status Pill Button with Hover Explanation */}
          <div 
            className="relative"
            onMouseEnter={() => setStatusHovered(true)}
            onMouseLeave={() => setStatusHovered(false)}
          >
            <button
              id="engine-status-toggle"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold select-none transition-all duration-300
                ${isOnline 
                  ? "bg-zinc-900 border-white/5 hover:border-white/10 text-zinc-300" 
                  : "bg-rose-950/20 border-rose-500/20 text-rose-300"
                }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse" : "bg-rose-500"}`} />
              <span>{isOnline ? "Engine Online" : "Engine Offline"}</span>
            </button>

            {/* Premium Informative Tooltip */}
            <AnimatePresence>
              {statusHovered && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="absolute right-0 mt-2.5 w-72 rounded-xl bg-zinc-900 border border-white/10 p-4 shadow-2xl z-50 text-left"
                >
                  <div className="flex items-center gap-2 mb-2 border-b border-white/5 pb-2">
                    {isOnline ? (
                      <Check size={14} className="text-emerald-400" />
                    ) : (
                      <AlertCircle size={14} className="text-rose-400" />
                    )}
                    <span className="text-xs font-bold text-zinc-100 uppercase tracking-wider font-sans">
                      {isOnline ? "Analytical Pipeline Ready" : "Connection Outage Detected"}
                    </span>
                  </div>

                  <p className="text-[11px] text-zinc-400 leading-relaxed font-sans mb-3">
                    {isOnline 
                      ? "The Next.js client is connected to DuckDB and FastAPI. Natural language SQL compiling, K-Means clustering, and exponential smoothing are fully active."
                      : "The Next.js client failed to reach the FastAPI endpoint at 'https://bot-api-production-7ddf.up.railway.app'."
                    }
                  </p>

                  {!isOnline && (
                    <div className="space-y-2 border-t border-white/5 pt-2 select-text">
                      <div className="flex items-start gap-1.5">
                        <Info size={11} className="text-zinc-500 flex-shrink-0 mt-0.5" />
                        <span className="text-[9px] font-bold text-zinc-400 uppercase">Primary Diagnosis:</span>
                      </div>
                      <ul className="list-none space-y-1.5 pl-1.5">
                        <li className="flex items-start gap-1 text-[10px] text-zinc-500 leading-tight">
                          <ChevronRight size={8} className="mt-1 flex-shrink-0" />
                          <span><strong>Railway Cold Start:</strong> The API service might be sleeping or spinning up. Try refreshing in 30 seconds.</span>
                        </li>
                        <li className="flex items-start gap-1 text-[10px] text-zinc-500 leading-tight">
                          <ChevronRight size={8} className="mt-1 flex-shrink-0" />
                          <span><strong>Missing/Incorrect URL:</strong> Verify 'NEXT_PUBLIC_API_URL' environment variable matches your active backend domain.</span>
                        </li>
                        <li className="flex items-start gap-1 text-[10px] text-zinc-500 leading-tight">
                          <ChevronRight size={8} className="mt-1 flex-shrink-0" />
                          <span><strong>CORS Configuration:</strong> Ensure API backend headers allow requests from your deployment origin.</span>
                        </li>
                      </ul>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </header>

        {/* Toast Notification */}
        <AnimatePresence>
          {notification && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={`absolute top-20 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl text-xs font-semibold shadow-2xl select-none
                ${notification.type === "success"
                  ? "bg-zinc-900 border border-white/10 text-zinc-200"
                  : "bg-rose-950/20 border border-rose-500/20 text-rose-300"
                }`}
            >
              {notification.type === "success" ? "✓ " : "⚠️ "}{notification.msg}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chat Area */}
        <div className="flex-1 min-h-0 overflow-y-auto chat-scroll px-6 py-6">
          {messages.length === 0 ? (
            <WelcomeHero />
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              <AnimatePresence>
                {messages.map(msg => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
              </AnimatePresence>
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="flex-shrink-0 px-6 pb-6 pt-3 border-t border-white/5 bg-zinc-950/20 backdrop-blur-md">
          <div className="max-w-3xl mx-auto">
            <ChatInput
              onSend={handleSend}
              isLoading={isLoading}
              disabled={!hasWorkbook}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
