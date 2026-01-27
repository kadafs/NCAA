"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
    TrendingUp,
    Award,
    Target,
    Hash,
    Calendar,
    ArrowUpRight,
    BarChart3,
    Clock,
    CheckCircle2,
    XCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { PerformanceMetric } from "@/types";
import { ForecastLineChart } from "@/components/dashboard/ForecastLineChart";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";

/**
 * Performance Page - Model transparency and historical results
 * 
 * Features:
 * - Overall metrics summary
 * - By-league breakdown
 * - Rolling win% chart
 * - Recent picks log
 */

const MOCK_METRICS: PerformanceMetric[] = [
    { league: "TOTAL", record: "142-98-4", roi: 12.4, profit: 4520, winPct: 59.2, trend: [55, 58, 62, 59, 61, 59] },
    { league: "nba", record: "45-32-1", roi: 8.2, profit: 1240, winPct: 58.4, trend: [52, 55, 58, 56, 59, 58] },
    { league: "ncaa", record: "62-41-2", roi: 15.1, profit: 2180, winPct: 60.2, trend: [58, 60, 63, 61, 62, 60] },
];

const RECENT_PICKS = [
    { id: "1", matchup: "LAL @ BOS", type: "TOTAL OVER", line: 234.5, result: "WIN", edge: "+3.7", date: "Jan 21" },
    { id: "2", matchup: "MIL @ PHI", type: "TOTAL UNDER", line: 228.0, result: "WIN", edge: "+5.1", date: "Jan 21" },
    { id: "3", matchup: "GSW @ SAC", type: "TOTAL OVER", line: 241.5, result: "LOSS", edge: "+2.2", date: "Jan 20" },
    { id: "4", matchup: "NYK @ MIA", type: "TOTAL OVER", line: 215.0, result: "WIN", edge: "+4.4", date: "Jan 20" },
    { id: "5", matchup: "DAL @ DEN", type: "TOTAL UNDER", line: 224.5, result: "WIN", edge: "+3.8", date: "Jan 19" },
    { id: "6", matchup: "PHX @ LAC", type: "TOTAL OVER", line: 229.0, result: "WIN", edge: "+2.9", date: "Jan 19" },
];

export default function Performance() {
    const [activeTab, setActiveTab] = useState("performance");
    const [selectedPeriod, setSelectedPeriod] = useState("30d");

    return (
        <div className="min-h-screen bg-dash-bg text-dash-text-primary">
            <LeftSidebar />

            <div className="lg:ml-16 xl:ml-20">
                {/* Header */}
                <header className="sticky top-0 z-30 bg-dash-bg/80 backdrop-blur-xl border-b border-dash-border">
                    <div className="px-4 py-4 md:px-6 lg:px-8">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-gold rounded-2xl flex items-center justify-center shadow-[0_0_20px_rgba(251,191,36,0.2)]">
                                    <Award className="w-6 h-6 text-dash-bg" />
                                </div>
                                <div>
                                    <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tighter">
                                        Model <span className="text-gold italic">Performance</span>
                                    </h1>
                                    <p className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase tracking-widest mt-1">
                                        Transparency & Historical Trust Protocol
                                    </p>
                                </div>
                            </div>

                            {/* Quick Stats */}
                            <div className="flex gap-3">
                                <div className="bg-dash-card border border-dash-border rounded-xl px-4 py-2 text-center">
                                    <span className="text-[9px] font-black text-dash-text-muted uppercase block">ROI</span>
                                    <span className="text-lg font-black text-dash-success">+12.4%</span>
                                </div>
                                <div className="bg-dash-card border border-dash-border rounded-xl px-4 py-2 text-center">
                                    <span className="text-[9px] font-black text-dash-text-muted uppercase block">Win Rate</span>
                                    <span className="text-lg font-black text-white">59.2%</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Content */}
                <main className="p-4 md:p-6 lg:p-8 pb-24 lg:pb-8">
                    <div className="max-w-[1400px] mx-auto space-y-8">

                        {/* Metrics Grid */}
                        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            {MOCK_METRICS.map((metric, idx) => (
                                <motion.div
                                    key={metric.league}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.1 }}
                                    className="bg-dash-card border border-dash-border rounded-2xl p-5 hover:border-gold/20 transition-all group"
                                >
                                    <div className="flex justify-between items-start mb-4">
                                        <span className={cn(
                                            "text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-tight",
                                            metric.league === "TOTAL"
                                                ? "bg-gold/10 text-gold border border-gold/20"
                                                : "bg-dash-bg-secondary border border-dash-border text-dash-text-muted"
                                        )}>
                                            {metric.league}
                                        </span>
                                        <div className="text-right">
                                            <span className="text-xs font-black text-white italic block">{metric.record}</span>
                                            <span className="text-[8px] font-bold text-dash-text-muted uppercase">Record</span>
                                        </div>
                                    </div>

                                    <div className="space-y-4">
                                        <div className="flex justify-between items-end">
                                            <div>
                                                <span className="text-[10px] font-bold text-dash-text-muted uppercase block">Yield</span>
                                                <span className="text-2xl font-black text-dash-success">{metric.roi}%</span>
                                            </div>
                                            <div className="w-20 h-8 flex items-end gap-0.5">
                                                {metric.trend.map((v, i) => (
                                                    <div
                                                        key={i}
                                                        className="flex-1 bg-dash-success/20 rounded-t group-hover:bg-dash-success/40 transition-colors"
                                                        style={{ height: `${(v / 70) * 100}%` }}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                        <div className="h-px bg-dash-border" />
                                        <div className="flex justify-between items-center text-[10px] font-bold uppercase">
                                            <span className="text-dash-text-muted">Profit</span>
                                            <span className="text-white">${metric.profit.toLocaleString()}</span>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </section>

                        {/* Chart & History Row */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

                            {/* Trend Chart */}
                            <div className="lg:col-span-8 bg-dash-card border border-dash-border rounded-3xl p-6 md:p-8">
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <h3 className="text-lg font-black text-white uppercase tracking-tight flex items-center gap-2">
                                            <BarChart3 className="w-5 h-5 text-cyan" />
                                            Rolling Win % Trend
                                        </h3>
                                        <p className="text-[10px] font-bold text-dash-text-muted uppercase tracking-widest">
                                            Multi-League Aggregated History
                                        </p>
                                    </div>
                                    <div className="flex gap-2">
                                        {["7d", "30d", "90d", "All"].map((period) => (
                                            <button
                                                key={period}
                                                onClick={() => setSelectedPeriod(period)}
                                                className={cn(
                                                    "px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase transition-all",
                                                    selectedPeriod === period
                                                        ? "bg-gold text-dash-bg"
                                                        : "bg-dash-bg-secondary border border-dash-border text-dash-text-muted hover:text-white"
                                                )}
                                            >
                                                {period}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="h-[280px] w-full">
                                    <ForecastLineChart
                                        height={280}
                                        showAnnotations={false}
                                        data={[
                                            { time: "Dec 1", awayVal: 52, homeVal: 55 },
                                            { time: "Dec 8", awayVal: 55, homeVal: 54 },
                                            { time: "Dec 15", awayVal: 58, homeVal: 57 },
                                            { time: "Dec 22", awayVal: 56, homeVal: 59 },
                                            { time: "Dec 29", awayVal: 61, homeVal: 58 },
                                            { time: "Jan 5", awayVal: 59, homeVal: 62 },
                                            { time: "Jan 12", awayVal: 62, homeVal: 60 },
                                            { time: "Jan 19", awayVal: 59, homeVal: 61 },
                                        ]}
                                    />
                                </div>
                            </div>

                            {/* Recent Picks */}
                            <div className="lg:col-span-4 bg-dash-card border border-dash-border rounded-3xl p-6 md:p-8">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-lg font-black text-white uppercase tracking-tight flex items-center gap-2">
                                        <Clock className="w-5 h-5 text-gold" />
                                        Recent Picks
                                    </h3>
                                    <button className="p-2 border border-dash-border rounded-xl hover:bg-dash-bg-secondary transition-colors">
                                        <ArrowUpRight className="w-4 h-4 text-dash-text-muted" />
                                    </button>
                                </div>

                                <div className="space-y-3">
                                    {RECENT_PICKS.map((pick) => (
                                        <div
                                            key={pick.id}
                                            className="flex flex-col gap-2 p-3 bg-dash-bg-secondary border border-dash-border rounded-xl group hover:border-gold/20 transition-all"
                                        >
                                            <div className="flex justify-between items-center">
                                                <span className="text-[9px] font-black text-dash-text-muted uppercase">{pick.date}</span>
                                                <span className={cn(
                                                    "flex items-center gap-1 text-[9px] font-black px-2 py-0.5 rounded-full uppercase",
                                                    pick.result === "WIN"
                                                        ? "bg-dash-success/10 text-dash-success"
                                                        : "bg-dash-danger/10 text-dash-danger"
                                                )}>
                                                    {pick.result === "WIN"
                                                        ? <CheckCircle2 className="w-3 h-3" />
                                                        : <XCircle className="w-3 h-3" />
                                                    }
                                                    {pick.result}
                                                </span>
                                            </div>
                                            <div className="flex justify-between items-end">
                                                <div>
                                                    <h4 className="text-xs font-black text-white uppercase">{pick.matchup}</h4>
                                                    <p className="text-[10px] font-bold text-dash-text-muted uppercase mt-0.5">
                                                        {pick.type} @ {pick.line}
                                                    </p>
                                                </div>
                                                <div className="text-right">
                                                    <span className="text-[8px] font-bold text-dash-text-muted uppercase block">Edge</span>
                                                    <span className="text-xs font-black text-gold">{pick.edge}</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                <button className="w-full mt-4 py-3 bg-dash-bg border border-dash-border rounded-xl text-[10px] font-black text-dash-text-muted hover:text-white uppercase tracking-widest transition-colors">
                                    Full History Log
                                </button>
                            </div>
                        </div>

                        {/* Trust Banner */}
                        <div className="p-6 md:p-8 bg-dash-card border border-dash-border rounded-3xl flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden">
                            <div className="flex items-center gap-6">
                                <div className="w-14 h-14 bg-cyan/10 rounded-full flex items-center justify-center border border-cyan/20">
                                    <Target className="w-7 h-7 text-cyan" />
                                </div>
                                <div>
                                    <h4 className="text-lg font-black text-white uppercase">Machine Precision. Human Trust.</h4>
                                    <p className="text-xs text-dash-text-muted max-w-md leading-relaxed mt-1">
                                        Our models are audited every 24 hours against moving market lines. We don't hide losses—we calculate variance and evolve.
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="flex -space-x-2">
                                    {[1, 2, 3, 4].map(i => (
                                        <div key={i} className="w-8 h-8 rounded-full border-2 border-dash-card bg-dash-bg-secondary flex items-center justify-center text-[8px] font-bold text-dash-text-muted">
                                            A{i}
                                        </div>
                                    ))}
                                </div>
                                <span className="text-[10px] font-black text-white uppercase">12,402 Analysts</span>
                            </div>
                            <div className="absolute top-0 right-0 p-6 opacity-5">
                                <Hash className="w-32 h-32" />
                            </div>
                        </div>
                    </div>
                </main>
            </div>

            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
    );
}
