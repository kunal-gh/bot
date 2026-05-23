"use client";

import { useState, useRef, KeyboardEvent, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Database, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (msg: string) => void;
  isLoading: boolean;
  hasWorkbook: boolean;
}

const SUGGESTIONS = [
  "Forecast revenue for the next 30 days",
  "Detect anomalies in my sales data",
  "Segment customers by order value",
  "What are the top 10 products by revenue?",
  "Show a summary of all transaction values",
  "Analyze monthly trend of quantity sold"
];

export function ChatInput({ onSend, isLoading, hasWorkbook }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value.trim() === "") {
      setFilteredSuggestions(SUGGESTIONS);
    } else {
      const query = value.toLowerCase();
      const filtered = SUGGESTIONS.filter(item => 
        item.toLowerCase().includes(query)
      );
      setFilteredSuggestions(filtered);
    }
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setValue("");
    setIsFocused(false);
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
    <div className="relative space-y-4 w-full select-none" ref={containerRef}>
      {/* Dynamic Suggestion Dropdown above the chatbox */}
      <AnimatePresence>
        {isFocused && filteredSuggestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 15 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="absolute bottom-full left-0 right-0 mb-3 rounded-2xl bg-zinc-900 border border-white/10 p-3 shadow-2xl z-50 max-h-56 overflow-y-auto chat-scroll space-y-1"
          >
            <div className="flex items-center gap-2 px-2 pb-2 mb-1 border-b border-white/5 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
              <HelpCircle size={12} />
              <span>Recommended Queries</span>
            </div>
            {filteredSuggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setValue(suggestion);
                  setIsFocused(false);
                  textareaRef.current?.focus();
                }}
                className="w-full text-left px-3 py-2 rounded-xl text-xs text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all duration-150 truncate cursor-pointer font-medium"
              >
                🔍 {suggestion}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Taller, Clickable Chatbox Container */}
      <div 
        className={cn(
          "relative flex items-end gap-3 rounded-2xl p-3.5 transition-all duration-300 bg-zinc-900 border cursor-text shadow-xl min-h-[64px]",
          isFocused ? "border-white/25 ring-2 ring-white/5" : "border-white/10 hover:border-white/15"
        )}
        onClick={() => textareaRef.current?.focus()}
      >
        <textarea
          ref={textareaRef}
          id="chat-input"
          value={value}
          onChange={e => { setValue(e.target.value); handleInput(); }}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          placeholder="Ask anything about your loaded dataset..."
          disabled={isLoading}
          rows={1}
          className="flex-1 resize-none bg-transparent text-base text-zinc-100 placeholder-zinc-500 outline-none px-3 py-2 leading-relaxed font-sans"
          style={{ maxHeight: "120px" }}
        />

        {/* Spacious premium Send Button */}
        <motion.button
          id="send-btn"
          whileTap={{ scale: 0.95 }}
          onClick={(e) => { e.stopPropagation(); handleSend(); }}
          disabled={!value.trim() || isLoading}
          className={cn(
            "flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-300 cursor-pointer shadow-lg",
            value.trim()
              ? "bg-white hover:bg-zinc-200 text-zinc-950 font-bold"
              : "bg-zinc-950 border border-white/5 text-zinc-700"
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

      <div className="flex items-center justify-between px-2">
        <p className="text-[9px] font-bold text-zinc-600 uppercase tracking-widest">
          Shift+Enter for new line · Enter to send
        </p>
        {!hasWorkbook && (
          <span className="flex items-center gap-1 text-[9px] font-bold text-amber-500 uppercase tracking-widest">
            <Database size={10} />
            Workbook Missing — Upload first
          </span>
        )}
      </div>
    </div>
  );
}
