"use client";

import React from "react";
import { motion } from "framer-motion";
import { Trophy, ChevronRight, Zap, Target, BarChart3, Globe } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

const LEAUGE_CARDS = [
  {
    id: "nba",
    name: "NBA",
    fullName: "National Basketball Association",
    icon: Zap,
    color: "text-amber-500",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    description: "High-volume pro modeling with star usage context."
  },
  {
    id: "ncaa",
    name: "NCAA",
    fullName: "Division I Men's Basketball",
    icon: Trophy,
    color: "text-blue-500",
    bg: "bg-blue-500/10",
    border: "border-blue-500/20",
    description: "Advanced efficiency analytics for 350+ D1 programs."
  },
  {
    id: "euro",
    name: "EURO",
    fullName: "European Leagues & EuroLeague",
    icon: Globe,
    color: "text-emerald-500",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    description: "International pace dampening and tactical modeling."
  }
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0b0c10] text-gray-200 flex flex-col items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Ambient Background Glows - Softer & More Discreet */}
      <div className="absolute top-[-15%] left-[-10%] w-[50%] h-[50%] bg-accent-blue/5 blur-[160px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-15%] right-[-10%] w-[50%] h-[50%] bg-accent-blue/3 blur-[160px] rounded-full pointer-events-none" />

      <div className="w-full max-w-5xl space-y-20 relative z-10">
        {/* Header */}
        <div className="text-center space-y-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center justify-center gap-4 mb-10"
          >
            <div className="bg-white/5 p-3 rounded-2xl border border-white/10 shadow-2xl shadow-black/50">
              <Trophy className="w-8 h-8 text-accent-blue" />
            </div>
            <h1 className="text-4xl md:text-5xl font-black tracking-tighter text-display text-white">
              UNIVERSAL<span className="text-accent-blue font-normal opacity-90">HUB</span>
            </h1>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.8 }}
            className="space-y-6"
          >
            <h2 className="text-5xl md:text-8xl font-black text-white tracking-tighter leading-[0.9] text-display">
              BEYOND THE <span className="text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40">ANALYTICS.</span>
            </h2>
            <p className="text-lg md:text-xl text-gray-500 font-medium max-w-2xl mx-auto leading-relaxed">
              Select a specialized intelligence pool to begin your analysis. Standardized <span className="text-white/80 font-bold">v1.6 Framework</span> active across all sectors.
            </p>
          </motion.div>
        </div>

        {/* League Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {LEAUGE_CARDS.map((league, i) => (
            <motion.div
              key={league.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + (i * 0.1), duration: 0.6 }}
            >
              <Link href={`/dashboard/${league.id}`} className="block group h-full">
                <div className={cn(
                  "glass p-10 rounded-[40px] border border-white/[0.04] h-full transition-all duration-700 bg-white/[0.01] hover:bg-white/[0.03] hover:border-white/[0.08] relative overflow-hidden group/card",
                  "hover:-translate-y-2 hover:shadow-2xl hover:shadow-black/60"
                )}>
                  <div className="relative z-10 space-y-8 h-full flex flex-col items-start">
                    <div className={cn("inline-flex p-4 rounded-[24px] border border-white/[0.05] bg-white/[0.02] shadow-inner transition-transform duration-500 group-hover/card:scale-110", `group-hover/card:border-${league.id === 'nba' ? 'amber' : i === 1 ? 'blue' : 'emerald'}-500/30`)}>
                      <league.icon className={cn("w-7 h-7", league.color)} />
                    </div>

                    <div className="space-y-2">
                      <h3 className="text-3xl font-black text-white tracking-tight text-display">{league.name}</h3>
                      <p className="text-[10px] font-bold text-gray-600 uppercase tracking-[0.2em]">{league.fullName}</p>
                    </div>

                    <p className="text-sm text-gray-400 font-medium leading-relaxed opacity-80 group-hover/card:opacity-100 transition-opacity">
                      {league.description}
                    </p>

                    <div className="mt-auto pt-8 flex items-center gap-2 font-bold text-[10px] uppercase tracking-widest text-gray-600 transition-all duration-300 group-hover/card:text-accent-blue group-hover/card:gap-4">
                      Initialize Core <ChevronRight className="w-3 h-3" />
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Footer Info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6 pt-12 border-t border-white/[0.04]"
        >
          <div className="flex items-center gap-3 group cursor-default">
            <div className="w-8 h-8 rounded-full bg-white/[0.02] border border-white/[0.05] flex items-center justify-center group-hover:bg-accent-blue/10 transition-colors">
              <BarChart3 className="w-4 h-4 text-gray-600 group-hover:text-accent-blue transition-colors" />
            </div>
            <span className="text-[10px] font-bold uppercase text-gray-600 tracking-widest">Standardized Metrics</span>
          </div>
          <div className="flex items-center gap-3 group cursor-default">
            <div className="w-8 h-8 rounded-full bg-white/[0.02] border border-white/[0.05] flex items-center justify-center group-hover:bg-accent-blue/10 transition-colors">
              <Target className="w-4 h-4 text-gray-600 group-hover:text-amber-500 transition-colors" />
            </div>
            <span className="text-[10px] font-bold uppercase text-gray-600 tracking-widest">Deterministic Logic</span>
          </div>
          <div className="flex items-center gap-3 group cursor-default">
            <div className="w-8 h-8 rounded-full bg-white/[0.02] border border-white/[0.05] flex items-center justify-center group-hover:bg-accent-blue/10 transition-colors">
              <Zap className="w-4 h-4 text-gray-600 group-hover:text-yellow-500 transition-colors" />
            </div>
            <span className="text-[10px] font-bold uppercase text-gray-600 tracking-widest">Real-time Props</span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
