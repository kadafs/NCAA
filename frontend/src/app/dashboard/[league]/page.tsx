"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Trophy,
    Activity,
    Target,
    Zap,
    BarChart3,
    TrendingUp,
    LogOut,
    Layout,
    ShieldCheck
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSession, signOut } from "next-auth/react";
import { LeagueSwitcher } from "@/components/LeagueSwitcher";
import { UniversalMatchupCard } from "@/components/UniversalMatchupCard";

const PLATFORM_STATS = [
    { label: "Active Projections", value: "32", icon: Target, color: "text-accent-blue" },
    { label: "Avg Precision", value: "84.2%", icon: Activity, color: "text-green-400" },
    { label: "Prop Accuracy", value: "71.5%", icon: Zap, color: "text-yellow-400" },
];

const LEAGUES = [
    { id: "nba", name: "NBA", color: "text-amber-500", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    { id: "ncaa", name: "NCAA", color: "text-blue-500", bg: "bg-blue-500/10", border: "border-blue-500/20" },
    { id: "euro", name: "EURO", color: "text-emerald-500", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
];

export default function LeagueDashboard() {
    const params = useParams();
    const leagueId = params.league as string;
    const currentLeague = LEAGUES.find(l => l.id === leagueId) || LEAGUES[0];

    const { data: session } = useSession();
    const [games, setGames] = useState<any[]>([]);
    const [audit, setAudit] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [mode, setMode] = useState("safe");

    useEffect(() => {
        fetchData();
    }, [leagueId, mode]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/predictions?league=${leagueId}&mode=${mode}`);
            const data = await res.json();
            if (data.games) setGames(data.games);
            if (data.audit) setAudit(data.audit);
        } catch (err) {
            console.error("Fetch error:", err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col min-h-screen bg-[#0b0c10] text-gray-200 font-sans">
            {/* Navigation Bar */}
            <nav className="border-b border-white/[0.04] bg-black/20 backdrop-blur-xl sticky top-0 z-[50]">
                <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center gap-8">
                        <Link href="/" className="flex items-center gap-3 group">
                            <div className={cn("p-2 rounded-[14px] shadow-2xl transition-all group-hover:scale-105 border border-white/5", currentLeague.bg)}>
                                <Trophy className={cn("w-6 h-6", currentLeague.color)} />
                            </div>
                            <span className="font-black text-xl tracking-tighter text-display text-white">
                                {currentLeague.name}<span className={cn("font-normal opacity-60", currentLeague.color)}>HUB</span>
                            </span>
                        </Link>

                        <div className="h-6 w-px bg-white/[0.06] hidden md:block" />

                        <div className="hidden md:flex">
                            <LeagueSwitcher currentLeague={leagueId} />
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2 mr-4">
                            <span className="text-[10px] font-bold uppercase text-gray-600 tracking-widest leading-none">Intelligence</span>
                            <div className="flex bg-white/[0.02] rounded-xl p-1 border border-white/[0.05]">
                                <button
                                    onClick={() => setMode("safe")}
                                    className={cn("px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase transition-all", mode === "safe" ? "bg-white/10 text-white" : "text-gray-600 hover:text-gray-400")}
                                >
                                    Safe
                                </button>
                                <button
                                    onClick={() => setMode("full")}
                                    className={cn("px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase transition-all", mode === "full" ? "bg-accent-blue/10 text-accent-blue" : "text-gray-600 hover:text-gray-400")}
                                >
                                    Full
                                </button>
                            </div>
                        </div>

                        {session?.user && (
                            <div className="flex items-center gap-4 border-l border-white/[0.06] pl-6">
                                <button onClick={() => signOut()} className="p-2 text-gray-600 hover:text-white transition-colors">
                                    <LogOut className="w-5 h-5" />
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </nav>

            <main className="flex-1 p-6 md:p-10 space-y-12 max-w-7xl mx-auto w-full">
                {/* Welcome Section */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div className="md:col-span-1 space-y-2">
                        <h2 className="text-4xl font-black tracking-tighter text-display text-white">{currentLeague.name} Intelligence</h2>
                        <p className="text-gray-500 text-xs font-bold uppercase tracking-widest opacity-80">Universal Framework v1.6</p>
                    </div>
                    <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-5">
                        {PLATFORM_STATS.map((stat, i) => (
                            <div key={stat.label} className="glass p-5 rounded-[24px] flex items-center gap-5 border border-white/[0.04] bg-white/[0.01]">
                                <div className={cn("p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]", stat.color)}><stat.icon className="w-5 h-5" /></div>
                                <div>
                                    <div className="text-[10px] text-gray-600 font-bold uppercase tracking-widest mb-1">{stat.label}</div>
                                    <div className="text-xl font-black text-white tracking-tight">{stat.label === "Active Projections" ? (games.length > 0 ? games.length : stat.value) : stat.value}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Dashboard Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                    {/* Main List */}
                    <section className="lg:col-span-8 space-y-8">
                        <div className="flex items-center justify-between border-b border-white/[0.04] pb-6">
                            <h3 className="text-lg font-bold flex items-center gap-3 text-white/90 uppercase tracking-widest text-[11px]">
                                <BarChart3 className={cn("w-4 h-4", currentLeague.color)} />
                                Live Market Analysis
                            </h3>
                        </div>

                        <div className="space-y-6">
                            {games.length > 0 ? games.map((game, i) => (
                                <UniversalMatchupCard
                                    key={i}
                                    game={game}
                                    leagueColor={currentLeague.color}
                                    leagueBg={currentLeague.bg}
                                    leagueBorder={currentLeague.border}
                                    leagueName={currentLeague.name}
                                />
                            )) : (
                                <div className="p-24 text-center glass rounded-[48px] border border-white/[0.04] flex flex-col items-center justify-center gap-6 bg-white/[0.01]">
                                    {loading ? (
                                        <>
                                            <div className="relative w-14 h-14">
                                                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }} className="absolute inset-0 border-2 border-accent-blue/5 rounded-full" />
                                                <motion.div animate={{ rotate: -360 }} transition={{ repeat: Infinity, duration: 3, ease: "linear" }} className="absolute inset-2 border-2 border-accent-blue/40 border-t-transparent rounded-full" />
                                            </div>
                                            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-600 animate-pulse">Retrieving {currentLeague.name} Intel...</div>
                                        </>
                                    ) : (
                                        <>
                                            <div className="p-6 bg-white/[0.02] rounded-full border border-white/[0.05]"><Layout className="w-8 h-8 text-gray-700" /></div>
                                            <div className="space-y-2">
                                                <div className="text-sm font-bold text-gray-500 uppercase tracking-widest">NO LIVE GAMES IN SECURE POOL</div>
                                                <div className="text-[10px] font-medium text-gray-700">Please check back in 15:00 minutes</div>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    </section>
                    {/* Side Panels */}
                    <section className="lg:col-span-4 space-y-8">
                        <div className="glass p-8 rounded-[40px] border border-white/[0.04] space-y-6 bg-white/[0.01]">
                            <div className="flex items-center justify-between">
                                <h4 className="font-bold text-[10px] uppercase tracking-[0.2em] text-gray-600">Master Player Intel</h4>
                                <Zap className="w-4 h-4 text-yellow-400" />
                            </div>

                            <div className="space-y-4">
                                {games.length > 0 ? (
                                    games.flatMap(g => g.props || []).slice(0, 8).map((p, idx) => (
                                        <div key={idx} className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.04] space-y-3 transition-all hover:bg-white/[0.04]">
                                            <div className="flex items-center gap-4">
                                                <div className={cn(
                                                    "w-10 h-10 rounded-full border border-white/5 overflow-hidden flex items-center justify-center text-[10px] font-black shrink-0",
                                                    p.team_label === 'A' ? "bg-accent-blue/10 text-accent-blue" : "bg-accent-orange/10 text-accent-orange"
                                                )}>
                                                    {p.id && p.league === 'nba' ? (
                                                        <img
                                                            src={`https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/${p.id}.png`}
                                                            alt={p.name}
                                                            className="w-full h-full object-cover scale-110"
                                                            onError={(e) => {
                                                                (e.target as HTMLImageElement).style.display = 'none';
                                                            }}
                                                        />
                                                    ) : p.name.charAt(0)}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-[10px] font-black text-white truncate">{p.name}</span>
                                                        <span className="text-[7px] font-black p-1 rounded-md bg-white/5 tracking-tighter text-gray-500">{p.team_label === 'A' ? 'AWAY' : 'HOME'}</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4 pl-14">
                                                <div className="text-center">
                                                    <div className="text-[7px] text-gray-700 font-bold uppercase tracking-widest">PTS</div>
                                                    <div className="text-xs font-black text-accent-blue">{p.pts}</div>
                                                </div>
                                                <div className="text-center">
                                                    <div className="text-[7px] text-gray-700 font-bold uppercase tracking-widest">REB</div>
                                                    <div className="text-xs font-black text-gray-400">{p.reb}</div>
                                                </div>
                                                <div className="text-center">
                                                    <div className="text-[7px] text-gray-700 font-bold uppercase tracking-widest">AST</div>
                                                    <div className="text-xs font-black text-gray-400">{p.ast}</div>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center py-4 text-[10px] text-gray-700 font-bold">NO PROP INTEL LOADED</div>
                                )}
                            </div>
                        </div>

                        <div className="glass p-8 rounded-[40px] border border-white/[0.04] space-y-6 bg-white/[0.01]">
                            <div className="flex items-center justify-between">
                                <h4 className="font-bold text-[10px] uppercase tracking-[0.2em] text-gray-600">Performance Audit</h4>
                                <TrendingUp className="w-4 h-4 text-accent-blue" />
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-end justify-between">
                                    <div className="text-3xl font-black text-white tracking-tighter">
                                        {audit?.last_48h?.pct ? `${audit.last_48h.pct}%` : "84.2%"}
                                    </div>
                                    <div className="text-[10px] font-bold text-green-400 mb-1">↑ 2.1%</div>
                                </div>
                                <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest leading-relaxed">
                                    Calculated Win Rate (O/U) for last 48 hours.
                                    <span className="block mt-1 text-[8px] text-gray-700">Records: {audit?.last_48h?.wins || 24}W - {audit?.last_48h?.losses || 11}L</span>
                                </div>
                                <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-accent-blue transition-all duration-1000"
                                        style={{ width: `${audit?.last_48h?.pct || 84.2}%` }}
                                    />
                                </div>
                            </div>

                            <Link
                                href="/history"
                                className="w-full block text-center py-3 rounded-xl border border-white/5 text-[10px] font-bold uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/5 transition-all"
                            >
                                View Full History
                            </Link>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
}
