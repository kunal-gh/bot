"use client";

import { motion } from "framer-motion";
import { Zap, BarChart3, Brain, Search } from "lucide-react";

const features = [
  {
    icon: <Brain size={16} className="text-zinc-400" />,
    title: "Natural Language Queries",
    desc: "Ask questions in plain English. BOT automatically compiles and runs optimal SQL.",
  },
  {
    icon: <BarChart3 size={16} className="text-zinc-400" />,
    title: "Time-Series Forecasting",
    desc: "Predict future variables using historical time-series modeling directly.",
  },
  {
    icon: <Search size={16} className="text-zinc-400" />,
    title: "Anomaly Detection",
    desc: "Find statistical outliers and understand the factors contributing to them.",
  },
  {
    icon: <Zap size={16} className="text-zinc-400" />,
    title: "Automated Clustering",
    desc: "Segment multidimensional datasets dynamically with K-Means clustering.",
  },
];

export function WelcomeHero() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 text-center select-none">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-2xl"
      >
        <div className="mb-6 flex items-center justify-center">
          <div className="h-10 w-10 rounded-xl bg-zinc-900 border border-white/10 flex items-center justify-center">
            <Zap size={18} className="text-zinc-300 animate-float" />
          </div>
        </div>

        <h2 className="text-4xl font-extrabold tracking-tight text-white mb-3">
          Beyond Ordinary Tables
        </h2>
        <p className="text-zinc-500 text-sm mb-10 max-w-md mx-auto leading-relaxed">
          An elegant engine designed for natural language data analysis. Upload any Excel workbook to perform deep queries, forecasting, and clustering.
        </p>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl mx-auto">
          {features.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05, duration: 0.5 }}
              className="bg-zinc-900/40 border border-white/5 rounded-xl p-5 text-left hover:border-white/10 transition-colors"
            >
              <div className="mb-3 w-8 h-8 rounded-lg bg-zinc-900 border border-white/5 flex items-center justify-center">{f.icon}</div>
              <p className="text-xs font-semibold text-zinc-100 mb-1">{f.title}</p>
              <p className="text-[11px] text-zinc-500 leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-10 text-[11px] text-zinc-600 tracking-wide uppercase"
        >
          ← Begin by uploading your workbook in the sidebar
        </motion.p>
      </motion.div>
    </div>
  );
}
