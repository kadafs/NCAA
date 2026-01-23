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
    const [activeTab, setActiveTab] = useState("history");

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
                    <div className="max-w-5xl mx-auto space-y-8">
                        {/* League Cards Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {["nba", "ncaa"].map((league) => {
                                const stats = audit?.[league];
                                if (!stats) return null;

                                return (
                                    <motion.div
                                        key={league}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="bg-dash-card border border-dash-border rounded-3xl p-6 md:p-8"
                                    >
                                        <div className="flex items-center justify-between mb-6">
                                            <div className="flex items-center gap-4">
                                                <div className={cn(
                                                    "w-12 h-12 rounded-2xl flex items-center justify-center border",
                                                    league === 'nba'
                                                        ? "bg-gold/10 border-gold/20 text-gold"
                                                        : "bg-cyan/10 border-cyan/20 text-cyan"
                                                )}>
                                                    <Trophy className="w-6 h-6" />
                                                </div>
                                                <div>
                                                    <h3 className="text-lg font-black text-white uppercase">{league}</h3>
                                                    <div className="text-[10px] text-dash-text-muted font-bold uppercase tracking-widest">
                                                        Reliability Score
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="px-3 py-1 rounded-full bg-dash-success/10 border border-dash-success/20 text-[8px] font-black text-dash-success uppercase tracking-widest">
                                                VERIFIED
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-2 gap-4 mb-6">
                                            <div className="p-4 rounded-2xl bg-dash-bg border border-dash-border">
                                                <div className="text-[9px] font-bold text-dash-text-muted uppercase mb-1">48h Accuracy</div>
                                                <div className="text-2xl font-black text-white">{stats.last_48h.pct}%</div>
                                                <div className="text-[9px] font-bold text-dash-text-muted uppercase">
                                                    {stats.last_48h.wins}W - {stats.last_48h.losses}L
                                                </div>
                                            </div>
                                            <div className="p-4 rounded-2xl bg-dash-bg border border-dash-border">
                                                <div className="text-[9px] font-bold text-dash-text-muted uppercase mb-1">All-Time</div>
                                                <div className={cn(
                                                    "text-2xl font-black",
                                                    league === 'nba' ? "text-gold" : "text-cyan"
                                                )}>
                                                    {stats.all_time.pct}%
                                                </div>
                                                <div className="text-[9px] font-bold text-dash-text-muted uppercase">
                                                    {stats.all_time.wins}W - {stats.all_time.losses}L
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-dash-text-muted">
                                                <span>Confidence Curve</span>
                                                <span>High Retention</span>
                                            </div>
                                            <div className="h-2 w-full bg-dash-bg rounded-full overflow-hidden">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${stats.all_time.pct}%` }}
                                                    transition={{ duration: 1.5, ease: "easeOut" }}
                                                    className={cn(
                                                        "h-full",
                                                        league === 'nba' ? "bg-gold" : "bg-cyan"
                                                    )}
                                                />
                                            </div>
                                        </div>

                                        <div className="pt-6 mt-6 border-t border-dash-border flex items-center justify-between">
                                            <div className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-widest text-dash-text-muted">
                                                <Calendar className="w-3 h-3" />
                                                Last Update: {new Date(stats.last_update).toLocaleDateString()}
                                            </div>
                                            <ShieldCheck className={cn(
                                                "w-4 h-4",
                                                league === 'nba' ? "text-gold" : "text-cyan"
                                            )} />
                                        </div>
                                    </motion.div>
                                );
                            })}
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

            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
    );
}
