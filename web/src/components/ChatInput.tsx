"use client";

// src/components/ChatInput.tsx
import { useState, useRef, KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { Send, Mic, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (msg: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

const QUICK_ACTIONS = [
  { icon: "📈", label: "Forecast", query: "Forecast revenue for the next 30 days" },
  { icon: "🔍", label: "Anomalies", query: "Detect anomalies in my sales data" },
  { icon: "🧩", label: "Cluster", query: "Segment customers by order value" },
  { icon: "🏆", label: "Top 10", query: "What are the top 10 products by revenue?" },
];

export function ChatInput({ onSend, isLoading, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isLoading || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  return (
    <div className="space-y-3">
      {/* Quick Action Pills */}
      {!disabled && (
        <div className="flex gap-2 flex-wrap">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              id={`quick-${action.label.toLowerCase()}`}
              onClick={() => { setValue(action.query); textareaRef.current?.focus(); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium text-slate-400 hover:text-white border border-white/8 hover:border-violet-500/40 hover:bg-violet-500/10 transition-all duration-200"
            >
              <span>{action.icon}</span>
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Input Box */}
      <div className={cn(
        "relative flex items-end gap-2 rounded-2xl p-2 transition-all duration-200",
        "glass-strong border",
        value.length > 0 ? "border-violet-500/40 glow-accent" : "border-white/10",
        disabled && "opacity-50"
      )}>
        <textarea
          ref={textareaRef}
          id="chat-input"
          value={value}
          onChange={e => { setValue(e.target.value); handleInput(); }}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Upload a workbook to start querying…" : "Ask anything about your data…"}
          disabled={disabled || isLoading}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm text-white placeholder-slate-600 outline-none px-3 py-2 leading-relaxed"
          style={{ maxHeight: "120px" }}
        />

        {/* Send Button */}
        <motion.button
          id="send-btn"
          whileTap={{ scale: 0.92 }}
          onClick={handleSend}
          disabled={!value.trim() || isLoading || disabled}
          className={cn(
            "flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200",
            value.trim() && !disabled
              ? "bg-gradient-to-br from-violet-600 to-cyan-500 text-white glow-accent"
              : "bg-white/5 text-slate-700"
          )}
        >
          {isLoading ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <Sparkles size={16} />
            </motion.div>
          ) : (
            <Send size={15} />
          )}
        </motion.button>
      </div>

      <p className="text-[10px] text-slate-700 text-center">
        Shift+Enter for new line · Enter to send
      </p>
    </div>
  );
}
