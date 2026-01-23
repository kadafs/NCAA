"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Prediction } from "@/types";
import { cn } from "@/lib/utils";
import { ChevronDown, Info, Zap, AlertTriangle, TrendingUp } from "lucide-react";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { CircularGauge } from "./CircularGauge";

interface PredictionCardProps {
    prediction: Prediction;
}

export function PredictionCard({ prediction }: PredictionCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div className="group flex flex-col bg-dash-card border border-dash-border rounded-2xl overflow-hidden transition-all duration-300 hover:border-white/10 hover:shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
            {/* Header: League & Confidence */}
            <div className="flex justify-between items-center p-4 bg-white/5 border-b border-dash-border">
                <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-dash-bg-secondary rounded text-[9px] font-black text-gold uppercase tracking-tighter">
                        {prediction.league}
                    </span>
                    <span className="text-[10px] font-bold text-dash-text-muted uppercase">
                        {prediction.date} | {prediction.time}
                    </span>
                </div>
                <ConfidenceBadge confidence={prediction.confidence} />
            </div>

            {/* Content: VS Layout */}
            <div className="p-6">
                <div className="flex flex-col md:flex-row items-center justify-between gap-8">
                    {/* Teams Row */}
                    <div className="flex items-center gap-6 w-full md:w-auto">
                        {/* Away */}
                        <div className="flex-1 flex flex-col items-center md:items-end text-center md:text-right gap-2">
                            <div className="w-16 h-16 bg-dash-bg-secondary rounded-2xl flex items-center justify-center p-2 border border-dash-border">
                                <img src={prediction.awayTeam.logo} alt={prediction.awayTeam.name} className="max-w-full max-h-full object-contain" />
                            </div>
                            <div>
                                <h3 className="text-xs font-black text-white uppercase leading-none">{prediction.awayTeam.name}</h3>
                                <p className="text-[10px] font-bold text-dash-text-muted mt-0.5">{prediction.awayTeam.record}</p>
                            </div>
                        </div>

                        {/* VS Divider */}
                        <div className="flex flex-col items-center gap-1">
                            <span className="text-xl font-black italic text-dash-text-muted group-hover:text-white transition-colors">VS</span>
                            <div className="h-12 w-[1px] bg-gradient-to-b from-transparent via-dash-border to-transparent" />
                        </div>

                        {/* Home */}
                        <div className="flex-1 flex flex-col items-center md:items-start text-center md:text-left gap-2">
                            <div className="w-16 h-16 bg-dash-bg-secondary rounded-2xl flex items-center justify-center p-2 border border-dash-border">
                                <img src={prediction.homeTeam.logo} alt={prediction.homeTeam.name} className="max-w-full max-h-full object-contain" />
                            </div>
                            <div>
                                <h3 className="text-xs font-black text-white uppercase leading-none">{prediction.homeTeam.name}</h3>
                                <p className="text-[10px] font-bold text-dash-text-muted mt-0.5">{prediction.homeTeam.record}</p>
                            </div>
                        </div>
                    </div>

                    {/* Stats/Gauges Section (Dynamic for Mobile/Desktop) */}
                    <div className="flex flex-wrap items-center justify-center gap-6">
                        <CircularGauge
                            value={prediction.homeTeam.stats.netRating}
                            label="Net Rating"
                            subLabel="Efficiency"
                            size={100}
                            strokeWidth={8}
                            color="#3B82F6"
                        />

                        <div className="flex flex-col items-center justify-center bg-dash-bg-secondary p-4 rounded-2xl border border-dash-border min-w-[140px]">
                            <span className="text-[9px] font-bold text-dash-text-muted uppercase mb-1">Market Line</span>
                            <span className="text-xl font-black text-white italic">{prediction.marketTotal}</span>
                            <div className="w-full h-px bg-dash-border my-2" />
                            <span className="text-[9px] font-bold text-dash-text-muted uppercase mb-1">Model Predict</span>
                            <span className="text-xl font-black text-gold italic">{prediction.modelTotal}</span>
                        </div>
                    </div>
                </div>

                {/* The "Big Edge" Highlight */}
                <div className="mt-8 flex items-center justify-between p-4 bg-gold/5 rounded-xl border border-gold/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gold rounded-full flex items-center justify-center text-dash-bg">
                            <Zap className="w-6 h-6 fill-current" />
                        </div>
                        <div>
                            <span className="text-[10px] font-black text-gold uppercase tracking-widest block">Model Edge Detected</span>
                            <span className="text-sm font-bold text-white uppercase tracking-tighter">
                                {prediction.edge > 0 ? "Potential OVER" : "Potential UNDER"} Play Recommended
                            </span>
                        </div>
                    </div>
                    <div className="text-right">
                        <span className="text-2xl font-black text-gold">+{prediction.edge}</span>
                        <span className="text-[8px] font-bold text-dash-text-muted uppercase block">Point Value</span>
                    </div>
                </div>

                {/* Expand Toggle */}
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full mt-4 flex items-center justify-center gap-2 py-2 text-[10px] font-bold text-dash-text-muted hover:text-white uppercase transition-colors"
                >
                    {isExpanded ? "Hide Details" : "View Detailed Trace & Math"}
                    <motion.div animate={{ rotate: isExpanded ? 180 : 0 }}>
                        <ChevronDown className="w-4 h-4" />
                    </motion.div>
                </button>

                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                        >
                            <div className="pt-6 border-t border-dash-border space-y-4">
                                {/* Trace List */}
                                <div className="space-y-2">
                                    <h4 className="text-[9px] font-black text-dash-text-muted uppercase tracking-widest mb-3">Model Logic Audit (Trace)</h4>
                                    {prediction.trace.map((step, idx) => (
                                        <div key={idx} className="flex items-start gap-3 p-2 bg-dash-bg-secondary/50 rounded-lg group/step">
                                            <span className="text-[10px] font-bold text-gold/60 mt-0.5">0{idx + 1}</span>
                                            <p className="text-[11px] font-medium text-dash-text-secondary leading-relaxed group-hover/step:text-white transition-colors">
                                                {step}
                                            </p>
                                        </div>
                                    ))}
                                </div>

                                {/* Factors Bar List */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 pt-4">
                                    {prediction.factors.map((factor, idx) => (
                                        <div key={idx} className="space-y-1.5">
                                            <div className="flex justify-between text-[9px] font-bold uppercase">
                                                <span className="text-dash-text-muted">{factor.label}</span>
                                                <span className={cn(
                                                    factor.impact === 'positive' ? "text-dash-success" :
                                                        factor.impact === 'negative' ? "text-dash-danger" : "text-dash-text-secondary"
                                                )}>
                                                    {factor.value}%
                                                </span>
                                            </div>
                                            <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${factor.value}%` }}
                                                    className={cn(
                                                        "h-full rounded-full",
                                                        factor.impact === 'positive' ? "bg-dash-success" :
                                                            factor.impact === 'negative' ? "bg-dash-danger" : "bg-cyan"
                                                    )}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
