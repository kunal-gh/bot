"use client";

// src/app/page.tsx — Main application page
import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, SchemaResponse, HealthResponse } from "@/lib/api";
import { SAMPLE_QUERIES } from "@/lib/utils";
import { AnimatedOrbs } from "@/components/ui/AnimatedOrbs";
import { Sidebar } from "@/components/Sidebar";
import { ChatMessage, Message } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { WelcomeHero } from "@/components/WelcomeHero";
import { Menu, X } from "lucide-react";

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
      }
    } catch {
      // backend offline — silent
    }
  }, []);

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 15000);
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

  return (
    <div className="relative flex h-screen overflow-hidden bg-[var(--bg-primary)]">
      <AnimatedOrbs />

      {/* ── Sidebar ── */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ type: "spring", damping: 30, stiffness: 250 }}
            className="relative z-10 w-64 flex-shrink-0 h-full glass-strong border-r border-white/5 p-4 flex flex-col"
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

      {/* ── Main Area ── */}
      <div className="relative z-10 flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top Bar */}
        <div className="flex-shrink-0 flex items-center gap-3 px-4 py-3 border-b border-white/5 glass-strong">
          <button
            id="sidebar-toggle"
            onClick={() => setSidebarOpen(v => !v)}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/10 transition-colors text-slate-500 hover:text-white"
          >
            {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
          </button>
          <div className="flex-1">
            <h1 className="text-sm font-bold text-white">BOT AI Analytics Agent</h1>
            <p className="text-[10px] text-slate-600">
              {hasWorkbook
                ? `${schema.tables.length} table${schema.tables.length > 1 ? "s" : ""} loaded · Ask anything`
                : "Upload an Excel workbook to begin"
              }
            </p>
          </div>

          {/* Status Dot */}
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${health?.duckdb_connected ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />
            <span className="text-[10px] text-slate-600 hidden sm:inline">
              {health?.duckdb_connected ? "Connected" : "Offline"}
            </span>
          </div>
        </div>

        {/* Notification Toast */}
        <AnimatePresence>
          {notification && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={`absolute top-16 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl text-sm font-medium shadow-2xl
                ${notification.type === "success"
                  ? "bg-green-500/20 border border-green-500/30 text-green-300"
                  : "bg-red-500/20 border border-red-500/30 text-red-300"
                }`}
            >
              {notification.type === "success" ? "✓ " : "⚠ "}{notification.msg}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chat Area */}
        <div className="flex-1 min-h-0 overflow-y-auto chat-scroll px-4 py-6">
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

        {/* Input Area */}
        <div className="flex-shrink-0 px-4 pb-4 pt-2 border-t border-white/5 glass-strong">
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
