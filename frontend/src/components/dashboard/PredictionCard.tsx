"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Prediction } from "@/types";
import { cn } from "@/lib/utils";
import { ChevronDown, Info, Zap, AlertTriangle, TrendingUp, Trophy } from "lucide-react";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { CircularGauge } from "./CircularGauge";
import { NCAA_LOGO_MAP } from "@/lib/ncaa-mappings";

interface PredictionCardProps {
    prediction: Prediction;
}

const LEAGUE_FALLBACKS: Record<string, string> = {
    nba: 'https://upload.wikimedia.org/wikipedia/en/0/03/National_Basketball_Association_logo.svg',
    ncaa: 'https://upload.wikimedia.org/wikipedia/commons/d/dd/NCAA_logo.svg',
    euro: 'https://upload.wikimedia.org/wikipedia/en/3/30/Euroleague_logo.svg',
    eurocup: 'https://upload.wikimedia.org/wikipedia/en/3/30/Euroleague_logo.svg',
    nbl: 'https://upload.wikimedia.org/wikipedia/en/d/d9/National_Basketball_League_%28Australia%29_logo.svg',
    acb: 'https://upload.wikimedia.org/wikipedia/en/d/df/Liga_ACB_logo.svg'
};

export function PredictionCard({ prediction }: PredictionCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [awayLogoError, setAwayLogoError] = useState(false);
    const [homeLogoError, setHomeLogoError] = useState(false);

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
                <div className="flex items-center gap-2">
                    <ConfidenceBadge confidence={prediction.confidence} />

                    {/* Polymarket Signal badge */}
                    {prediction.polymarket && (() => {
                        const prices = prediction.polymarket.prices.map(Number);
                        const outcomes = prediction.polymarket.outcomes;
                        const total = prediction.polymarket.total;

                        // For O/U markets: outcomes = ["Over", "Under"], prices = [over_prob, under_prob]
                        const overProb = outcomes[0] === "Over" ? prices[0] : prices[1];
                        const underProb = outcomes[1] === "Under" ? prices[1] : prices[0];

                        // Determine which side has higher probability
                        const favored = overProb > underProb ? "Over" : "Under";
                        const favoredProb = Math.max(overProb, underProb);
                        const prob = Math.round(favoredProb * 100);

                        return (
                            <a
                                href={prediction.polymarket.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1.5 px-2 py-0.5 bg-[#2B3040] hover:bg-[#343A4B] border border-white/5 rounded transition-colors group/poly"
                                title={`Polymarket: ${favored} ${total} (${prob}% probability)`}
                            >
                                <img src="https://polymarket.com/favicon.ico" alt="Poly" className="w-3 h-3 grayscale group-hover/poly:grayscale-0" />
                                <span className="text-[9px] font-bold text-gray-400 group-hover/poly:text-white uppercase transition-colors">
                                    {favored} {total}: {prob}%
                                </span>
                            </a>
                        );
                    })()}
                </div>
            </div>

            {/* Content: VS Layout */}
            <div className="p-4 sm:p-6">
                <div className="flex flex-col xl:flex-row items-center justify-between gap-4 sm:gap-6 xl:gap-8">
                    {/* Teams Row */}
                    <div className="flex items-center justify-center gap-3 sm:gap-6 w-full xl:w-auto">
                        {/* Away */}
                        <div className="flex-1 flex flex-col items-center xl:items-end text-center xl:text-right gap-1 sm:gap-2 min-w-0">
                            <div className="w-12 h-12 sm:w-16 sm:h-16 bg-dash-bg-secondary rounded-xl sm:rounded-2xl flex items-center justify-center p-1.5 sm:p-2 border border-dash-border flex-shrink-0">
                                <img
                                    src={prediction.awayTeam.logo || LEAGUE_FALLBACKS[prediction.league?.toLowerCase()] || LEAGUE_FALLBACKS.ncaa}
                                    alt={prediction.awayTeam.name}
                                    onError={(e) => {
                                        const target = e.target as HTMLImageElement;
                                        const league = prediction.league?.toLowerCase() || 'ncaa';
                                        const fallback = LEAGUE_FALLBACKS[league] || LEAGUE_FALLBACKS.ncaa;

                                        if (league === 'ncaa') {
                                            const rawName = prediction.awayTeam.name.toLowerCase().trim();
                                            const cleanName = NCAA_LOGO_MAP[rawName] || rawName.replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                                            const smartUrl = `/api/logo/${cleanName}`;

                                            // Start: Prevent infinite loop if smart URL also fails
                                            // If the current src is already the smart URL, or the fallback, stop.
                                            if (target.src === smartUrl || target.src === fallback) {
                                                if (target.src !== fallback) target.src = fallback;
                                                return;
                                            }

                                            // Try smart URL
                                            target.src = smartUrl;
                                            return;
                                        }

                                        if (target.src === fallback) return;
                                        target.src = fallback;
                                    }}
                                    className="max-w-full max-h-full object-contain"
                                />
                            </div>
                            <div className="min-w-0 w-full">
                                <h3 className="text-[11px] sm:text-xs font-black text-white uppercase leading-tight truncate max-w-full xl:max-w-[160px]">{prediction.awayTeam.name}</h3>
                                <p className="text-[9px] sm:text-[10px] font-bold text-dash-text-muted mt-0.5">{prediction.awayTeam.record}</p>
                            </div>
                        </div>

                        {/* VS Divider */}
                        <div className="flex flex-col items-center gap-1 flex-shrink-0">
                            <span className="text-base sm:text-xl font-black italic text-dash-text-muted group-hover:text-white transition-colors">VS</span>
                            <div className="h-8 sm:h-12 w-[1px] bg-gradient-to-b from-transparent via-dash-border to-transparent" />
                        </div>

                        {/* Home */}
                        <div className="flex-1 flex flex-col items-center xl:items-start text-center xl:text-left gap-1 sm:gap-2 min-w-0">
                            <div className="w-12 h-12 sm:w-16 sm:h-16 bg-dash-bg-secondary rounded-xl sm:rounded-2xl flex items-center justify-center p-1.5 sm:p-2 border border-dash-border flex-shrink-0">
                                <img
                                    src={prediction.homeTeam.logo || LEAGUE_FALLBACKS[prediction.league?.toLowerCase()] || LEAGUE_FALLBACKS.ncaa}
                                    alt={prediction.homeTeam.name}
                                    onError={(e) => {
                                        const target = e.target as HTMLImageElement;
                                        const league = prediction.league?.toLowerCase() || 'ncaa';
                                        const fallback = LEAGUE_FALLBACKS[league] || LEAGUE_FALLBACKS.ncaa;

                                        if (league === 'ncaa') {
                                            const cleanName = prediction.homeTeam.name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                                            const smartUrl = `/api/logo/${cleanName}`;

                                            if (target.src === smartUrl || target.src === fallback) {
                                                if (target.src !== fallback) target.src = fallback;
                                                return;
                                            }

                                            target.src = smartUrl;
                                            return;
                                        }

                                        if (target.src === fallback) return;
                                        target.src = fallback;
                                    }}
                                    className="max-w-full max-h-full object-contain"
                                />
                            </div>
                            <div className="min-w-0 w-full">
                                <h3 className="text-[11px] sm:text-xs font-black text-white uppercase leading-tight truncate max-w-full xl:max-w-[160px]">{prediction.homeTeam.name}</h3>
                                <p className="text-[9px] sm:text-[10px] font-bold text-dash-text-muted mt-0.5">{prediction.homeTeam.record}</p>
                            </div>
                        </div>
                    </div>

                    {/* Stats/Gauges Section (Dynamic for Mobile/Desktop) */}
                    <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-6 w-full xl:w-auto mt-4 xl:mt-0">
                        <div className="hidden sm:block">
                            <CircularGauge
                                value={prediction.homeTeam.stats.netRating}
                                label="Net Rating"
                                subLabel="Efficiency"
                                size={80}
                                strokeWidth={6}
                                color="#3B82F6"
                            />
                        </div>
                        {/* Mobile-only compact gauge */}
                        <div className="sm:hidden">
                            <CircularGauge
                                value={prediction.homeTeam.stats.netRating}
                                label="Rating"
                                size={64}
                                strokeWidth={5}
                                color="#3B82F6"
                            />
                        </div>

                        <div className="flex flex-col items-center justify-center bg-dash-bg-secondary p-3 sm:p-4 rounded-xl sm:rounded-2xl border border-dash-border w-[120px] sm:w-[140px]">
                            <span className="text-[8px] sm:text-[9px] font-bold text-dash-text-muted uppercase mb-0.5 sm:mb-1">Market Line</span>
                            <span className="text-lg sm:text-xl font-black text-white italic">{prediction.marketTotal}</span>
                            <div className="w-full h-px bg-dash-border my-1.5 sm:my-2" />
                            <span className="text-[8px] sm:text-[9px] font-bold text-dash-text-muted uppercase mb-0.5 sm:mb-1">Model Predict</span>
                            <span className="text-lg sm:text-xl font-black text-gold italic">{prediction.modelTotal}</span>
                            {prediction.rawModelTotal && Math.abs(prediction.rawModelTotal - prediction.modelTotal) > 0.5 && (
                                <span className="text-[7px] sm:text-[8px] font-bold text-dash-text-muted mt-1">Raw: {prediction.rawModelTotal}</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* The "Big Edge" Highlight */}
                <div className={cn(
                    "mt-4 sm:mt-8 flex flex-col sm:flex-row items-start sm:items-center justify-between p-3 sm:p-4 rounded-xl border transition-silky gap-3 sm:gap-4",
                    (prediction.confidence === 'NO PLAY' || prediction.confidence === 'PASS')
                        ? "bg-white/5 border-white/10 opacity-60"
                        : (prediction.decision === 'LEAN' || prediction.confidence === 'LEAN')
                            ? "bg-gold/5 border-gold/10"
                            : "bg-gold/10 border-gold/20 shadow-lg shadow-gold/5"
                )}>
                    <div className="flex items-center gap-3 sm:gap-4 min-w-0 flex-1">
                        <div className={cn(
                            "w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center flex-shrink-0",
                            prediction.confidence === 'NO PLAY' ? "bg-white/10" : "bg-gold/20"
                        )}>
                            <TrendingUp className={cn(
                                "w-5 h-5 sm:w-6 sm:h-6",
                                prediction.confidence === 'NO PLAY' ? "text-dash-text-muted" : "text-gold"
                            )} />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className={cn(
                                "text-[10px] sm:text-xs font-bold uppercase tracking-wider",
                                prediction.confidence === 'NO PLAY' ? "text-dash-text-muted" : "text-gold/60"
                            )}>
                                Model Edge Detected
                            </p>
                            <p className={cn(
                                "text-sm sm:text-lg font-black leading-tight",
                                prediction.confidence === 'NO PLAY' ? "text-dash-text-muted" : "text-white"
                            )}>
                                <span className="hidden sm:inline">
                                    {prediction.side ? `POTENTIAL ${prediction.side}` : prediction.edge > 0 ? "POTENTIAL OVER" : "POTENTIAL UNDER"}
                                    {prediction.decision === 'LEAN' ? " LEAN" :
                                        prediction.decision === 'PASS' ? " PASS" : " PLAY"} RECOMMENDED
                                </span>
                                <span className="sm:hidden">
                                    {prediction.side || (prediction.edge > 0 ? "OVER" : "UNDER")}
                                    {prediction.decision === 'LEAN' ? " LEAN" :
                                        prediction.decision === 'PASS' ? " PASS" : " PLAY"}
                                </span>
                            </p>
                        </div>
                    </div>
                    <div className="text-left sm:text-right flex sm:flex-col items-center sm:items-end gap-2 sm:gap-0 flex-shrink-0">
                        <span className={cn(
                            "text-xl sm:text-2xl font-black",
                            prediction.confidence === 'NO PLAY' ? "text-dash-text-muted" : "text-gold"
                        )}>
                            {prediction.edge > 0 ? `+${prediction.edge}` : prediction.edge}
                        </span>
                        <p className="text-[9px] sm:text-[10px] text-dash-text-muted font-bold uppercase">Point Value</p>
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
