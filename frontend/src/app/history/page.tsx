"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Trophy, BarChart3, Calendar, ShieldCheck, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";

/**
 * History Page - Model Reliability Audit (Dark Theme)
 * 
 * Displays historical accuracy and verification data
 */

export default function PerformanceHistory() {
    const [audit, setAudit] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [selectedFilter, setSelectedFilter] = useState<string>("TOTAL");

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
            // Mock data for demo
            setAudit({
                nba: {
                    last_48h: { wins: 24, losses: 11, pct: 68.6 },
                    all_time: { wins: 156, losses: 89, pct: 63.7 },
                    last_update: new Date().toISOString()
                },
                ncaa: {
                    last_48h: { wins: 32, losses: 18, pct: 64.0 },
                    all_time: { wins: 234, losses: 121, pct: 65.9 },
                    last_update: new Date().toISOString()
                }
            });
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-dash-bg flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                        className="w-12 h-12 border-2 border-gold/20 border-t-gold rounded-full"
                    />
                    <span className="text-[10px] font-bold text-dash-text-muted uppercase tracking-widest">
                        Loading History...
                    </span>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-dash-bg text-dash-text-primary">
            <LeftSidebar />

            <div className="lg:ml-16 xl:ml-20">
                {/* Header */}
                <header className="sticky top-0 z-30 bg-dash-bg/80 backdrop-blur-xl border-b border-dash-border">
                    <div className="px-4 py-4 md:px-6 lg:px-8">
                        <Link
                            href="/dashboard"
                            className="inline-flex items-center gap-2 text-[10px] font-bold text-dash-text-muted uppercase tracking-widest hover:text-white transition-colors mb-4 group"
                        >
                            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-1 transition-transform" />
                            Back to Dashboard
                        </Link>

                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 bg-cyan/10 border border-cyan/20 rounded-2xl flex items-center justify-center">
                                <ShieldCheck className="w-6 h-6 text-cyan" />
                            </div>
                            <div>
                                <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tighter">
                                    Model <span className="text-cyan italic">Audit</span>
                                </h1>
                                <p className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase tracking-widest mt-1">
                                    Historical Reliability Protocol
                                </p>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Content */}
                <main className="p-4 md:p-6 lg:p-8 pb-24 lg:pb-8">
                    <div className="max-w-6xl mx-auto space-y-8">
                        {/* League Cards Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {audit?.metrics?.map((m: any) => (
                                <motion.div
                                    key={m.league}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    onClick={() => setSelectedFilter(selectedFilter === m.league ? "TOTAL" : m.league)}
                                    className={cn(
                                        "bg-dash-card border rounded-3xl p-6 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]",
                                        selectedFilter === m.league
                                            ? "border-gold shadow-[0_0_20px_rgba(251,191,36,0.1)]"
                                            : "border-dash-border hover:border-gold/30"
                                    )}
                                >
                                    <div className="flex items-center justify-between mb-6">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-xl flex items-center justify-center border bg-gold/10 border-gold/20 text-gold">
                                                <Trophy className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <h3 className="text-sm font-black text-white uppercase">{m.league}</h3>
                                                <div className="text-[8px] text-dash-text-muted font-bold uppercase tracking-widest">
                                                    Reliability Score
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3 mb-6">
                                        <div className="p-3 rounded-xl bg-dash-bg border border-dash-border">
                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase mb-1">Accuracy</div>
                                            <div className="text-xl font-black text-white">{m.win_pct}%</div>
                                        </div>
                                        <div className="p-3 rounded-xl bg-dash-bg border border-dash-border">
                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase mb-1">Record</div>
                                            <div className="text-xl font-black text-gold">
                                                {m.wins}-{m.losses}-{m.pushes}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <div className="h-1.5 w-full bg-dash-bg rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${m.win_pct}%` }}
                                                className="h-full bg-gold"
                                            />
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>

                        {/* Full History Log */}
                        <div className="bg-dash-card border border-dash-border rounded-3xl overflow-hidden">
                            <div className="p-6 md:p-8 border-b border-dash-border flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Calendar className="w-5 h-5 text-gold" />
                                    <h4 className="text-lg font-black text-white uppercase">
                                        {selectedFilter === "TOTAL" ? "Full History Log" : `${selectedFilter} Results`}
                                    </h4>
                                </div>
                                <div className="flex items-center gap-4">
                                    {selectedFilter !== "TOTAL" && (
                                        <button
                                            onClick={() => setSelectedFilter("TOTAL")}
                                            className="text-[9px] font-black text-gold uppercase tracking-widest border border-gold/20 px-2 py-1 rounded-lg hover:bg-gold/10 transition-colors"
                                        >
                                            Clear Filter
                                        </button>
                                    )}
                                    <span className="text-[10px] font-bold text-dash-text-muted uppercase">Verified Results Only</span>
                                </div>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="bg-white/5 border-b border-dash-border">
                                            <th className="px-6 py-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">Date</th>
                                            <th className="px-6 py-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">League</th>
                                            <th className="px-6 py-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">Mode</th>
                                            <th className="px-6 py-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">Matchup</th>
                                            <th className="px-6 py-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">Line</th>
                                            <th className="px-6 py-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest text-gold">Model Predict</th>
                                            <th className="px-6 py-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">Outcome</th>
                                            <th className="px-6 py-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">Result</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-dash-border">
                                        {audit?.recent?.filter((p: any) => {
                                            if (selectedFilter === "TOTAL") return true;

                                            // Handle special mode cases like ncaa_full
                                            const l = p.league.toLowerCase();
                                            const m = (p.mode || 'safe').toLowerCase();

                                            if (selectedFilter.toLowerCase().includes('_full')) {
                                                const baseLeague = selectedFilter.toLowerCase().replace('_full', '');
                                                return l === baseLeague && m === 'full';
                                            } else {
                                                // Handle 'ncaa' which should match league=ncaa AND mode=safe
                                                // or 'nba' which should match league=nba AND mode=safe
                                                return l === selectedFilter.toLowerCase() && m === 'safe';
                                            }
                                        }).map((p: any) => (
                                            <tr key={p.id} className="hover:bg-white/[0.02] transition-colors">
                                                <td className="px-6 py-4 text-xs font-bold text-dash-text-muted uppercase">{p.game_date}</td>
                                                <td className="px-6 py-4">
                                                    <span className="text-[10px] font-black px-2 py-0.5 bg-dash-bg border border-dash-border rounded text-gold uppercase">
                                                        {p.league}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={cn(
                                                        "text-[10px] font-black px-2 py-0.5 rounded uppercase border",
                                                        (p.mode || 'safe') === 'full'
                                                            ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                                                            : "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                                                    )}>
                                                        {p.mode || 'SAFE'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-xs font-black text-white uppercase">{p.matchup}</td>
                                                <td className="px-6 py-4 text-xs font-bold text-dash-text-muted uppercase">{p.market_total}</td>
                                                <td className="px-6 py-4 text-xs font-black text-gold italic">{p.model_total}</td>
                                                <td className="px-6 py-4 text-xs font-black text-white">{p.actual_total}</td>
                                                <td className="px-6 py-4">
                                                    <span className={cn(
                                                        "text-[9px] font-black px-2 py-0.5 rounded uppercase",
                                                        p.is_win === true ? "bg-dash-success/20 text-dash-success" :
                                                            p.is_win === false ? "bg-dash-danger/20 text-dash-danger" :
                                                                "bg-dash-text-muted/20 text-dash-text-muted"
                                                    )}>
                                                        {p.is_win === true ? "WIN" : p.is_win === false ? "LOSS" : "PUSH"}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                        {!audit?.recent?.length && (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-12 text-center text-xs font-bold text-dash-text-muted uppercase tracking-widest bg-dash-bg/30">
                                                    No results archived yet. Real results will appear here after the first audit.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Methodology Card */}
                        <div className="bg-dash-card border border-dash-border rounded-3xl p-6 md:p-8">
                            <div className="flex items-center gap-3 mb-4">
                                <BarChart3 className="w-5 h-5 text-gold" />
                                <h4 className="text-lg font-black text-white uppercase">Data Methodology</h4>
                            </div>
                            <p className="text-sm text-dash-text-muted leading-relaxed">
                                Predictions are locked at game-start based on the "Live Market" total at that timestamp.
                                Accuracy is calculated using a deterministic O/U delta: any prediction within 0.5 points
                                of the final score is considered a "Push" and excluded from Win/Loss totals.
                                All results are independently verifiable against public box scores.
                            </p>
                        </div>
                    </div>
                </main>
            </div>

            <BottomNav />
        </div>
    );
}
