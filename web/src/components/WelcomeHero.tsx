"use client";

// src/components/WelcomeHero.tsx
import { motion } from "framer-motion";
import { Zap, BarChart3, Brain, Search } from "lucide-react";

const features = [
  {
    icon: <Brain size={18} className="text-violet-400" />,
    title: "Natural Language Queries",
    desc: "Ask in plain English — BOT translates to SQL automatically",
  },
  {
    icon: <BarChart3 size={18} className="text-cyan-400" />,
    title: "ML Forecasting",
    desc: "Predict future trends with time-series models",
  },
  {
    icon: <Search size={18} className="text-amber-400" />,
    title: "Anomaly Detection",
    desc: "Isolation Forest auto-detects outliers and explains why",
  },
  {
    icon: <Zap size={18} className="text-green-400" />,
    title: "Auto Clustering",
    desc: "K-Means segments customers and products automatically",
  },
];

export function WelcomeHero() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        {/* Animated Logo */}
        <div className="relative w-24 h-24 mx-auto mb-6">
          <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-violet-600 to-cyan-500 opacity-20 blur-xl animate-pulse-glow" />
          <div className="relative w-full h-full rounded-3xl bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center glow-accent">
            <Zap size={40} className="text-white animate-float" />
          </div>
        </div>

        <h2 className="text-3xl font-bold gradient-text mb-2">BOT Analytics</h2>
        <p className="text-slate-500 text-sm mb-8 max-w-md">
          Upload any Excel workbook and start asking questions in plain English.
          BOT will join tables, detect anomalies, forecast trends, and explain everything.
        </p>

        {/* Feature Grid */}
        <div className="grid grid-cols-2 gap-3 max-w-lg w-full">
          {features.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.08, duration: 0.4 }}
              className="glass rounded-2xl p-4 text-left gradient-border"
            >
              <div className="mb-2">{f.icon}</div>
              <p className="text-xs font-semibold text-white mb-1">{f.title}</p>
              <p className="text-[11px] text-slate-500 leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-xs text-slate-700"
        >
          ← Upload an Excel file from the sidebar to get started
        </motion.p>
      </motion.div>
    </div>
  );
}
