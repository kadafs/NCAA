"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Trophy, ArrowLeft, BarChart3, TrendingUp, Calendar, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export default function PerformanceHistory() {
    const [audit, setAudit] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAudit();
    }, []);

    const fetchAudit = async () => {
        try {
            const res = await fetch("/api/audit");
            const data = await res.json();
            setAudit(data);
        } catch (err) {
            console.error("Audit fetch error:", err);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-[#0b0c10] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                        className="w-12 h-12 border-2 border-accent-blue/20 border-t-accent-blue rounded-full"
                    />
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em]">Loading History...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#0b0c10] text-gray-200 font-sans p-6 md:p-12">
            <div className="max-w-5xl mx-auto space-y-12">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
                    <div className="space-y-4">
                        <Link
                            href="/dashboard/nba"
                            className="flex items-center gap-2 text-[10px] font-bold text-gray-500 uppercase tracking-widest hover:text-white transition-colors group"
                        >
                            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-1 transition-transform" />
                            Back to Core
                        </Link>
                        <h1 className="text-5xl font-black text-white tracking-tighter text-display">Model Reliability <span className="text-accent-blue">Audit</span></h1>
                        <p className="text-sm text-gray-500 font-medium max-w-xl leading-relaxed">
                            Live transparency into the mathematical framework's historical accuracy across all supported leagues. Updated in real-time as games conclude.
                        </p>
                    </div>
                </div>

                {/* Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                    {["nba", "ncaa"].map((league) => {
                        const stats = audit?.[league];
                        if (!stats) return null;

                        return (
                            <motion.div
                                key={league}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="glass p-10 rounded-[44px] border border-white/[0.04] bg-white/[0.01] space-y-10"
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className={cn(
                                            "w-12 h-12 rounded-2xl flex items-center justify-center border",
                                            league === 'nba' ? "bg-amber-500/10 border-amber-500/20 text-amber-500" : "bg-blue-500/10 border-blue-500/20 text-blue-500"
                                        )}>
                                            <Trophy className="w-6 h-6" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-black text-white tracking-tight uppercase">{league} Engineering</h3>
                                            <div className="text-[10px] text-gray-600 font-bold uppercase tracking-widest">Historical Reliability</div>
                                        </div>
                                    </div>
                                    <div className="px-3 py-1 rounded-full bg-green-500/5 border border-green-500/10 text-[8px] font-black text-green-400 uppercase tracking-widest">
                                        VERIFIED
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-6">
                                    <div className="p-6 rounded-[28px] bg-white/[0.02] border border-white/[0.04] space-y-3">
                                        <div className="text-[9px] font-black text-gray-600 uppercase tracking-widest">48h Accuracy</div>
                                        <div className="text-4xl font-black text-white tracking-tighter">{stats.last_48h.pct}%</div>
                                        <div className="text-[9px] font-bold text-gray-500 uppercase tracking-tighter">{stats.last_48h.wins}W - {stats.last_48h.losses}L</div>
                                    </div>
                                    <div className="p-6 rounded-[28px] bg-white/[0.02] border border-white/[0.04] space-y-3">
                                        <div className="text-[9px] font-black text-gray-600 uppercase tracking-widest">All-Time Accuracy</div>
                                        <div className="text-4xl font-black text-accent-blue tracking-tighter">{stats.all_time.pct}%</div>
                                        <div className="text-[9px] font-bold text-gray-500 uppercase tracking-tighter">{stats.all_time.wins}W - {stats.all_time.losses}L</div>
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-gray-500">
                                        <span>Confidence Curve</span>
                                        <span>High Retention</span>
                                    </div>
                                    <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${stats.all_time.pct}%` }}
                                            transition={{ duration: 1.5, ease: "easeOut" }}
                                            className="h-full bg-gradient-to-r from-accent-blue to-cyan-400"
                                        />
                                    </div>
                                </div>

                                <div className="pt-8 border-t border-white/[0.04] flex items-center justify-between opacity-50">
                                    <div className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-widest text-gray-600">
                                        <Calendar className="w-3 h-3" />
                                        Last Update: {new Date(stats.last_update).toLocaleDateString()}
                                    </div>
                                    <ShieldCheck className="w-4 h-4 text-accent-blue" />
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                <div className="glass p-12 rounded-[44px] border border-white/[0.04] bg-white/[0.01] flex flex-col md:flex-row items-center gap-10">
                    <div className="flex-1 space-y-4 text-center md:text-left">
                        <div className="flex items-center gap-2 text-[10px] font-bold text-accent-blue uppercase tracking-[0.2em] justify-center md:justify-start">
                            <BarChart3 className="w-4 h-4" />
                            Data Methodology
                        </div>
                        <h4 className="text-2xl font-black text-white tracking-tighter">How we calculate accuracy.</h4>
                        <p className="text-xs text-gray-500 leading-relaxed font-medium">
                            Predictions are locked at game-start based on the "Live Market" total at that timestamp. Accuracy is calculated using a deterministic O/U delta: any prediction within 0.5 points of the final score is considered a "Push" and excluded from Win/Loss totals.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
