"use client";

import { motion } from "framer-motion";
import { Database, BarChart3, ShieldAlert, Sparkles } from "lucide-react";

export function WelcomeHero() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center select-none py-12">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-3xl"
      >
        {/* Massive Premium Title */}
        <h1 className="text-8xl md:text-9xl font-black tracking-tighter text-white mb-6 uppercase select-none font-sans leading-none">
          BOT
        </h1>
        
        <p className="text-zinc-400 text-base md:text-lg mb-12 max-w-xl mx-auto leading-relaxed font-sans font-medium">
          An elegant analytical terminal for structured Excel data.
        </p>

        {/* Minimal Premium Capability List */}
        <div className="flex flex-col md:flex-row items-center justify-center gap-6 max-w-2xl mx-auto text-left border-t border-b border-white/5 py-8">
          <div className="flex gap-3 items-start max-w-xs">
            <div className="p-2.5 rounded-xl bg-zinc-900 border border-white/5 text-zinc-400 flex-shrink-0 mt-0.5">
              <Database size={15} />
            </div>
            <div>
              <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-wider mb-1">SQL Compiler</h4>
              <p className="text-[10px] text-zinc-500 leading-normal">Compiles plain-English questions into complex relational queries instantly.</p>
            </div>
          </div>

          <div className="flex gap-3 items-start max-w-xs">
            <div className="p-2.5 rounded-xl bg-zinc-900 border border-white/5 text-zinc-400 flex-shrink-0 mt-0.5">
              <BarChart3 size={15} />
            </div>
            <div>
              <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-wider mb-1">Forecasting</h4>
              <p className="text-[10px] text-zinc-500 leading-normal">Applies mathematical exponential smoothing for projection modeling.</p>
            </div>
          </div>

          <div className="flex gap-3 items-start max-w-xs">
            <div className="p-2.5 rounded-xl bg-zinc-900 border border-white/5 text-zinc-400 flex-shrink-0 mt-0.5">
              <ShieldAlert size={15} />
            </div>
            <div>
              <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-wider mb-1">Anomalies</h4>
              <p className="text-[10px] text-zinc-500 leading-normal">Runs Isolation Forests to segment and flag transaction outliers.</p>
            </div>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-12 flex items-center justify-center gap-2 text-[10px] text-zinc-500 tracking-widest uppercase font-bold"
        >
          <Sparkles size={11} className="text-zinc-600 animate-pulse" />
          <span>Select chat input to explore recommended queries</span>
        </motion.div>
      </motion.div>
    </div>
  );
}
