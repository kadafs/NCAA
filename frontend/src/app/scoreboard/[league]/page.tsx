"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    BarChart3,
    Trophy,
    Calendar,
    Zap,
    Activity,
    Clock,
    Tv,
    LayoutDashboard
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSession } from "next-auth/react";
import { LeagueSwitcher } from "@/components/LeagueSwitcher";

const LEAGUES = [
    { id: "nba", name: "NBA", color: "text-amber-500", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    { id: "ncaa", name: "NCAA", color: "text-blue-500", bg: "bg-blue-500/10", border: "border-blue-500/20" },
    { id: "euro", name: "EURO", color: "text-emerald-500", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
];

export default function ScoreboardPage() {
    const params = useParams();
    const leagueId = params.league as string;
    const currentLeague = LEAGUES.find(l => l.id === leagueId) || LEAGUES[0];

    const { data: session } = useSession();
    const user = session?.user as any;
    const [games, setGames] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const getETDate = (date: Date = new Date()) => {
        return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York' }).format(date);
    };

    const [selectedDate, setSelectedDate] = useState(getETDate());
    const [dates, setDates] = useState<string[]>([]);

    useEffect(() => {
        const d = [];
        const baseDate = new Date();
        for (let i = -3; i <= 3; i++) {
            const date = new Date(baseDate);
            date.setDate(date.getDate() + i);
            d.push(getETDate(date));
        }
        setDates(d);
    }, []);

    useEffect(() => {
        fetchScoreboard();
        const timer = setInterval(fetchScoreboard, 30000);
        return () => clearInterval(timer);
    }, [selectedDate, leagueId]);

    const fetchScoreboard = async () => {
        setLoading(true);
        try {
            // Updated to support league parameter
            const res = await fetch(`/api/predictions?league=${leagueId}&date=${selectedDate}`);
            const data = await res.json();
            if (data.games) setGames(data.games);
            else setGames([]);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr: string) => {
        const d = new Date(dateStr);
        return {
            day: d.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase(),
            num: d.getDate(),
            month: d.toLocaleDateString('en-US', { month: 'short' }).toUpperCase()
        };
    };

    return (
        <div className="min-h-screen bg-[#0b0c10] text-white font-sans selection:bg-accent-blue/30">
            {/* Navigation Header */}
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

                        <div className="hidden md:flex items-center gap-1 bg-white/[0.02] p-1 rounded-2xl border border-white/[0.04]">
                            <Link href={`/dashboard/${leagueId}`} className="px-5 py-2 rounded-xl text-xs font-semibold text-gray-500 hover:text-gray-300 transition-all">Dashboard</Link>
                            <Link href={`/scoreboard/${leagueId}`} className={cn("px-5 py-2 rounded-xl text-xs font-semibold shadow-sm ring-1 ring-white/5", currentLeague.bg, currentLeague.color)}>Scoreboard</Link>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <LeagueSwitcher currentLeague={leagueId} />
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto p-6 md:p-10 space-y-12">
                {/* Date Section */}
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-3xl font-black tracking-tighter text-display text-white flex items-center gap-4">
                            <Calendar className={cn("w-7 h-7", currentLeague.color)} />
                            Live Performance Tracking
                        </h2>
                        <div className="text-[10px] font-bold text-gray-600 uppercase tracking-widest bg-white/[0.02] px-4 py-1.5 rounded-full border border-white/[0.05]">
                            Updates every 30s • v1.6
                        </div>
                    </div>

                    <div className="flex items-center gap-4 overflow-x-auto pb-4 scrollbar-hide no-scrollbar -mx-2 px-2">
                        {dates.map((date, i) => {
                            const { day, num, month } = formatDate(date);
                            const isActive = selectedDate === date;
                            return (
                                <button
                                    key={date}
                                    onClick={() => setSelectedDate(date)}
                                    className={cn(
                                        "flex-shrink-0 w-24 py-5 rounded-[28px] flex flex-col items-center justify-center transition-all duration-500 border",
                                        isActive
                                            ? `${currentLeague.bg} border-white/[0.1] shadow-2xl shadow-black/40 -translate-y-1`
                                            : "bg-white/[0.01] border-white/[0.03] text-gray-600 hover:bg-white/[0.03] hover:border-white/[0.06] hover:text-gray-400"
                                    )}
                                >
                                    <span className={cn("text-[9px] font-bold uppercase tracking-widest leading-none mb-1", isActive ? "text-white/60" : "text-gray-700")}>{day}</span>
                                    <span className={cn("text-2xl font-black text-display tracking-tight", isActive ? "text-white" : "text-gray-400")}>{num}</span>
                                    <span className={cn("text-[9px] font-bold uppercase tracking-widest leading-none mt-1 opacity-60", isActive ? "text-white/80" : "text-gray-700")}>{month}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Scoreboard Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    <AnimatePresence mode="popLayout">
                        {loading && games.length === 0 ? (
                            Array.from({ length: 6 }).map((_, i) => (
                                <div key={i} className="glass h-56 rounded-[40px] animate-pulse border border-white/[0.04] bg-white/[0.01]" />
                            ))
                        ) : games.length > 0 ? (
                            games.map((game, i) => (
                                <motion.div
                                    key={i}
                                    layoutId={String(i)}
                                    initial={{ opacity: 0, y: 15 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: i * 0.05 }}
                                    className="glass rounded-[40px] border border-white/[0.04] overflow-hidden group hover:bg-white/[0.02] hover:border-white/[0.08] transition-all duration-500 relative cursor-default"
                                >
                                    <div className="px-6 py-4 bg-white/[0.02] flex items-center justify-between border-b border-white/[0.04]">
                                        <div className="flex items-center gap-2">
                                            {game.status === "LIVE" ? (
                                                <span className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-green-500/10 text-green-400 text-[9px] font-black border border-green-500/10 animate-pulse">
                                                    <Activity className="w-3 h-3" /> LIVE
                                                </span>
                                            ) : (
                                                <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest opacity-60">
                                                    {game.status === "FINAL" ? "FINAL" : game.startTime || "UPCOMING"}
                                                </span>
                                            )}
                                        </div>
                                        {game.tv && (
                                            <div className="flex items-center gap-1.5 text-gray-600 opacity-60 group-hover:opacity-100 transition-opacity">
                                                <Tv className="w-3 h-3" />
                                                <span className="text-[9px] font-bold uppercase tracking-tight">{game.tv}</span>
                                            </div>
                                        )}
                                    </div>

                                    <div className="p-8 space-y-6">
                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <span className="text-xl font-black text-display text-white group-hover:text-accent-blue transition-colors duration-500">{game.away}</span>
                                                <span className={cn("text-3xl font-mono font-black tracking-tighter", game.status === "PRE" ? "text-gray-800" : "text-white")}>
                                                    {game.awayScore || 0}
                                                </span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span className="text-xl font-black text-display text-white group-hover:text-accent-blue transition-colors duration-500">{game.home}</span>
                                                <span className={cn("text-3xl font-mono font-black tracking-tighter", game.status === "PRE" ? "text-gray-800" : "text-white")}>
                                                    {game.homeScore || 0}
                                                </span>
                                            </div>
                                        </div>

                                        {(game.status === "LIVE" || game.status === "FINAL") && (
                                            <div className="flex items-center justify-center gap-4 py-3 bg-white/[0.02] rounded-2xl border border-white/[0.04] group-hover:bg-white/[0.04] transition-colors">
                                                <div className="flex items-center gap-2">
                                                    <Clock className="w-3.5 h-3.5 text-accent-blue opacity-50" />
                                                    <span className="text-[10px] font-bold text-accent-blue uppercase tracking-[0.2em]">{game.clock || 'FULL'}</span>
                                                </div>
                                            </div>
                                        )}

                                        {game.model_total && (
                                            <div className="pt-6 border-t border-white/[0.06] flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <div className="bg-accent-blue/5 p-2 rounded-xl ring-1 ring-accent-blue/10">
                                                        <Zap className="w-3.5 h-3.5 text-accent-blue fill-accent-blue/30" />
                                                    </div>
                                                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest group-hover:text-white/60 transition-colors">AI Prediction</div>
                                                </div>
                                                <div className="text-xs font-mono font-black text-accent-blue bg-accent-blue/5 px-3 py-1 rounded-lg ring-1 ring-accent-blue/10 shadow-[0_0_20px_rgba(59,130,246,0.1)]">
                                                    {game.model_total}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))
                        ) : (
                            <div className="col-span-full py-32 text-center glass rounded-[60px] border border-white/[0.04] space-y-8 bg-white/[0.01]">
                                <div className="w-24 h-24 bg-white/[0.02] rounded-full flex items-center justify-center mx-auto border border-white/[0.05] shadow-inner">
                                    <Calendar className="w-10 h-10 text-gray-800" />
                                </div>
                                <div className="space-y-3">
                                    <h3 className="text-3xl font-black text-display text-white tracking-tight">No Games Scheduled</h3>
                                    <p className="text-gray-600 text-sm font-medium tracking-tight max-w-sm mx-auto">
                                        Check back later for live intelligence and AI models in the <span className="text-white opacity-60">v1.6 Framework</span>
                                    </p>
                                </div>
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}
