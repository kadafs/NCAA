"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    BarChart3,
    ChevronLeft,
    ChevronRight,
    Tv,
    Clock,
    Activity,
    Calendar,
    Zap,
    LayoutDashboard,
    Trophy,
    Loader2,
    Lock
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export default function ScoreboardPage() {
    const [games, setGames] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [dates, setDates] = useState<string[]>([]);
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        const savedUser = localStorage.getItem("ncaa_user");
        if (savedUser) setUser(JSON.parse(savedUser));

        // Generate date range
        const d = [];
        for (let i = -3; i <= 3; i++) {
            const date = new Date();
            date.setDate(date.getDate() + i);
            d.push(date.toISOString().split('T')[0]);
        }
        setDates(d);
    }, []);

    useEffect(() => {
        fetchScoreboard();
        const timer = setInterval(fetchScoreboard, 30000); // Poll every 30s
        return () => clearInterval(timer);
    }, [selectedDate]);

    const fetchScoreboard = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/predictions?date=${selectedDate}`);
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
        <div className="min-h-screen bg-[#050505] text-white font-sans selection:bg-accent-blue/30">
            {/* Navigation Header */}
            <nav className="border-b border-white/5 bg-black/40 backdrop-blur-md sticky top-0 z-[50]">
                <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <Link href="/" className="flex items-center gap-3 group">
                            <div className="bg-accent-blue p-2 rounded-xl shadow-lg shadow-accent-blue/20 group-hover:scale-110 transition-all">
                                <Trophy className="w-6 h-6 text-white" />
                            </div>
                            <span className="font-black text-xl tracking-tighter uppercase italic">NCAA<span className="text-accent-blue not-italic">HUB</span></span>
                        </Link>

                        <div className="h-6 w-px bg-white/10 hidden md:block" />

                        <div className="hidden md:flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/5">
                            <Link href="/" className="px-4 py-1.5 rounded-lg text-sm font-bold text-gray-500 hover:text-white transition-all">Dashboard</Link>
                            <Link href="/scoreboard" className="px-4 py-1.5 rounded-lg text-sm font-bold bg-accent-blue text-white shadow-lg shadow-accent-blue/20">Scoreboard</Link>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {user?.isPro && (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-accent-blue/10 border border-accent-blue/20 rounded-full">
                                <Zap className="w-3.5 h-3.5 text-accent-blue fill-accent-blue" />
                                <span className="text-[10px] font-black uppercase text-accent-blue tracking-wider">PRO Member</span>
                            </div>
                        )}
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto p-6 md:p-8 space-y-8">
                {/* Date Section */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-black flex items-center gap-3">
                            <Calendar className="w-6 h-6 text-accent-blue" />
                            LIVE SCOREBOARD
                        </h2>
                        <div className="text-xs font-bold text-gray-500 uppercase tracking-widest bg-white/5 px-3 py-1 rounded-full border border-white/5">
                            Updates every 30s
                        </div>
                    </div>

                    <div className="flex items-center gap-3 overflow-x-auto pb-2 scrollbar-hide no-scrollbar">
                        {dates.map((date) => {
                            const { day, num, month } = formatDate(date);
                            const isActive = selectedDate === date;
                            return (
                                <button
                                    key={date}
                                    onClick={() => setSelectedDate(date)}
                                    className={cn(
                                        "flex-shrink-0 w-20 py-4 rounded-2xl flex flex-col items-center justify-center transition-all border",
                                        isActive
                                            ? "bg-accent-blue border-accent-blue shadow-xl shadow-accent-blue/20 scale-105"
                                            : "bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10"
                                    )}
                                >
                                    <span className={cn("text-[10px] font-black", isActive ? "text-white/80" : "text-gray-500")}>{day}</span>
                                    <span className="text-xl font-black">{num}</span>
                                    <span className={cn("text-[9px] font-bold uppercase tracking-widest", isActive ? "text-white/70" : "text-gray-600")}>{month}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Scoreboard Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <AnimatePresence mode="popLayout">
                        {loading && games.length === 0 ? (
                            Array.from({ length: 6 }).map((_, i) => (
                                <div key={i} className="glass h-48 rounded-3xl animate-pulse border border-white/5" />
                            ))
                        ) : games.length > 0 ? (
                            games.map((game, i) => (
                                <motion.div
                                    key={game.id}
                                    layoutId={game.id}
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    whileHover={{ y: -5 }}
                                    className="glass rounded-3xl border border-white/5 overflow-hidden group hover:border-accent-blue/30 transition-all cursor-pointer"
                                >
                                    {/* Top Bar: TV / Status */}
                                    <div className="px-5 py-3 bg-white/5 flex items-center justify-between border-b border-white/5">
                                        <div className="flex items-center gap-2">
                                            {game.status === "LIVE" ? (
                                                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-[10px] font-black border border-red-500/30 animate-pulse">
                                                    <Activity className="w-3 h-3" /> LIVE
                                                </span>
                                            ) : (
                                                <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                                                    {game.status === "FINAL" ? "FINAL" : game.startTime || "UPCOMING"}
                                                </span>
                                            )}
                                        </div>
                                        {game.tv && (
                                            <div className="flex items-center gap-1.5 text-gray-500">
                                                <Tv className="w-3.5 h-3.5" />
                                                <span className="text-[10px] font-bold uppercase">{game.tv}</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Teams Area */}
                                    <div className="p-6 space-y-4">
                                        <div className="space-y-3">
                                            {/* Away Team */}
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    {game.awayRank && <span className="text-[10px] font-bold text-gray-500">#{game.awayRank}</span>}
                                                    <span className="text-lg font-black group-hover:text-accent-blue transition-colors">{game.away}</span>
                                                </div>
                                                <span className={cn("text-2xl font-mono font-black", game.status === "PRE" ? "text-gray-700" : "text-white")}>
                                                    {game.awayScore}
                                                </span>
                                            </div>
                                            {/* Home Team */}
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    {game.homeRank && <span className="text-[10px] font-bold text-gray-500">#{game.homeRank}</span>}
                                                    <span className="text-lg font-black group-hover:text-accent-blue transition-colors">{game.home}</span>
                                                </div>
                                                <span className={cn("text-2xl font-mono font-black", game.status === "PRE" ? "text-gray-700" : "text-white")}>
                                                    {game.homeScore}
                                                </span>
                                            </div>
                                        </div>

                                        {/* Clock / Period Info */}
                                        {(game.status === "LIVE" || game.status === "FINAL") && (
                                            <div className="flex items-center justify-center gap-4 py-2 bg-black/30 rounded-xl border border-white/5">
                                                <div className="flex items-center gap-1.5">
                                                    <Clock className="w-3 h-3 text-accent-blue" />
                                                    <span className="text-[10px] font-black text-accent-blue uppercase tracking-widest">{game.clock || 'FULL'}</span>
                                                </div>
                                                <div className="w-1 h-1 rounded-full bg-white/20" />
                                                <span className="text-[10px] font-black text-gray-400 uppercase">{game.period}</span>
                                            </div>
                                        )}

                                        {/* Prediction Integration */}
                                        {game.predictions?.advanced && (
                                            <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <div className="bg-accent-blue/20 p-1.5 rounded-lg">
                                                        <Zap className="w-3 h-3 text-accent-blue fill-accent-blue" />
                                                    </div>
                                                    <div className="text-[10px] font-black text-accent-blue uppercase tracking-widest">AI Prediction</div>
                                                </div>
                                                <div className="text-[11px] font-bold">
                                                    {game.predictions.advanced.scoreA} - {game.predictions.advanced.scoreH}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))
                        ) : (
                            <div className="col-span-full py-20 text-center glass rounded-3xl border border-white/5 space-y-4">
                                <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto border border-white/10">
                                    <Calendar className="w-10 h-10 text-gray-700" />
                                </div>
                                <div className="space-y-1">
                                    <h3 className="text-xl font-bold">No Games Scheduled</h3>
                                    <p className="text-gray-500 text-sm">Check back later for live intelligence</p>
                                </div>
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}
