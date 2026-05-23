"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { Send, Sparkles } from "lucide-react";
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
    <div className="space-y-3 select-none">
      {/* Quick Action Pills */}
      {!disabled && (
        <div className="flex gap-2 flex-wrap">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              id={`quick-${action.label.toLowerCase()}`}
              onClick={() => { setValue(action.query); textareaRef.current?.focus(); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[10px] font-semibold text-zinc-400 hover:text-white bg-zinc-900/40 border border-white/5 hover:border-white/10 transition-all duration-200"
            >
              <span>{action.icon}</span>
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Input Box */}
      <div className={cn(
        "relative flex items-end gap-2 rounded-xl p-2 transition-all duration-200",
        "bg-zinc-900/60 border",
        value.length > 0 ? "border-white/20" : "border-white/5",
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
          className="flex-1 resize-none bg-transparent text-sm text-zinc-100 placeholder-zinc-600 outline-none px-3 py-2 leading-relaxed font-sans"
          style={{ maxHeight: "120px" }}
        />

        {/* Send Button */}
        <motion.button
          id="send-btn"
          whileTap={{ scale: 0.95 }}
          onClick={handleSend}
          disabled={!value.trim() || isLoading || disabled}
          className={cn(
            "flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-200 cursor-pointer",
            value.trim() && !disabled
              ? "bg-zinc-100 hover:bg-white text-zinc-950 font-semibold"
              : "bg-zinc-900 border border-white/5 text-zinc-700"
          )}
        >
          {isLoading ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <Sparkles size={14} />
            </motion.div>
          ) : (
            <Send size={13} />
          )}
        </motion.button>
      </div>

      <p className="text-[9px] font-semibold text-zinc-600 text-center tracking-wide uppercase">
        Shift+Enter for new line · Enter to send
      </p>
    </div>
  );
}
