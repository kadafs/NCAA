"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Calendar,
    Activity,
    Clock,
    Tv,
    Zap,
    Trophy,
    ChevronLeft,
    ChevronRight
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";

/**
 * League Scoreboard - Dark Theme
 * 
 * Live scoreboard for a specific league with date navigation
 */

const LEAGUES = [
    { id: "nba", name: "NBA" },
    { id: "ncaa", name: "NCAA" },
];

export default function LeagueScoreboard() {
    const params = useParams();
    const leagueId = (params.league as string) || "nba";
    const currentLeague = LEAGUES.find(l => l.id === leagueId) || LEAGUES[0];

    const [games, setGames] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState("live");

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
            const res = await fetch(`/api/predictions?league=${leagueId}&date=${selectedDate}`);
            const data = await res.json();
            if (data.games) {
                setGames(data.games);
            } else {
                // Mock data for demo
                setGames([
                    { id: "1", away: "LAL", home: "BOS", awayScore: 102, homeScore: 108, status: "LIVE", clock: "Q4 2:34", model_total: 238.5, tv: "ESPN" },
                    { id: "2", away: "MIA", home: "NYK", awayScore: 0, homeScore: 0, status: "PRE", startTime: "7:30 PM", model_total: 215.0 },
                    { id: "3", away: "GSW", home: "PHX", awayScore: 112, homeScore: 118, status: "FINAL", model_total: 229.5, tv: "TNT" },
                ]);
            }
        } catch (err) {
            console.error(err);
            // Mock data for demo
            setGames([
                { id: "1", away: "LAL", home: "BOS", awayScore: 102, homeScore: 108, status: "LIVE", clock: "Q4 2:34", model_total: 238.5, tv: "ESPN" },
            ]);
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
        <div className="min-h-screen bg-dash-bg text-dash-text-primary">
            <LeftSidebar />

            <div className="lg:ml-16 xl:ml-20">
                {/* Header */}
                <header className="sticky top-0 z-30 bg-dash-bg/80 backdrop-blur-xl border-b border-dash-border">
                    <div className="px-4 py-4 md:px-6 lg:px-8">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-cyan/10 border border-cyan/20 rounded-2xl flex items-center justify-center">
                                    <Activity className="w-6 h-6 text-cyan" />
                                </div>
                                <div>
                                    <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tighter">
                                        {currentLeague.name} <span className="text-cyan italic">Live</span>
                                    </h1>
                                    <p className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase tracking-widest mt-1">
                                        Live Scoreboard • Updates every 30s
                                    </p>
                                </div>
                            </div>

                            {/* League Tabs */}
                            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
                                {LEAGUES.map((league) => (
                                    <Link
                                        key={league.id}
                                        href={`/scoreboard/${league.id}`}
                                        className={cn(
                                            "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all whitespace-nowrap",
                                            league.id === leagueId
                                                ? "bg-cyan text-dash-bg"
                                                : "bg-dash-card border border-dash-border text-dash-text-muted hover:text-white"
                                        )}
                                    >
                                        {league.name}
                                    </Link>
                                ))}
                            </div>
                        </div>

                        {/* Date Selector */}
                        <div className="flex items-center gap-2 mt-4 overflow-x-auto no-scrollbar pb-1">
                            {dates.map((date) => {
                                const { day, num, month } = formatDate(date);
                                const isActive = selectedDate === date;
                                return (
                                    <button
                                        key={date}
                                        onClick={() => setSelectedDate(date)}
                                        className={cn(
                                            "flex-shrink-0 w-16 md:w-20 py-3 rounded-xl flex flex-col items-center justify-center transition-all border",
                                            isActive
                                                ? "bg-gold/10 border-gold/20 -translate-y-0.5"
                                                : "bg-dash-card border-dash-border hover:border-gold/10"
                                        )}
                                    >
                                        <span className={cn(
                                            "text-[8px] font-bold uppercase tracking-wide",
                                            isActive ? "text-gold" : "text-dash-text-muted"
                                        )}>
                                            {day}
                                        </span>
                                        <span className={cn(
                                            "text-lg font-black",
                                            isActive ? "text-white" : "text-dash-text-secondary"
                                        )}>
                                            {num}
                                        </span>
                                        <span className={cn(
                                            "text-[8px] font-bold uppercase",
                                            isActive ? "text-gold/60" : "text-dash-text-muted"
                                        )}>
                                            {month}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </header>

                {/* Content */}
                <main className="p-4 md:p-6 lg:p-8 pb-24 lg:pb-8">
                    <div className="max-w-[1400px] mx-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
                            <AnimatePresence mode="popLayout">
                                {loading && games.length === 0 ? (
                                    Array.from({ length: 6 }).map((_, i) => (
                                        <div
                                            key={i}
                                            className="bg-dash-card border border-dash-border rounded-3xl h-52 animate-pulse"
                                        />
                                    ))
                                ) : games.length > 0 ? (
                                    games.map((game, i) => (
                                        <motion.div
                                            key={game.id || i}
                                            layoutId={String(game.id || i)}
                                            initial={{ opacity: 0, y: 15 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ duration: 0.4, delay: i * 0.05 }}
                                            className="bg-dash-card border border-dash-border rounded-3xl overflow-hidden hover:border-gold/20 transition-all group"
                                        >
                                            {/* Card Header */}
                                            <div className="px-4 py-3 bg-dash-bg border-b border-dash-border flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    {game.status === "LIVE" ? (
                                                        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 text-[9px] font-black uppercase border border-red-500/20">
                                                            <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
                                                            LIVE
                                                        </span>
                                                    ) : game.status === "FINAL" ? (
                                                        <span className="text-[9px] font-bold text-dash-text-muted uppercase">FINAL</span>
                                                    ) : (
                                                        <span className="text-[9px] font-bold text-dash-text-muted uppercase">{game.startTime || "UPCOMING"}</span>
                                                    )}
                                                </div>
                                                {game.tv && (
                                                    <div className="flex items-center gap-1.5 text-dash-text-muted">
                                                        <Tv className="w-3 h-3" />
                                                        <span className="text-[9px] font-bold uppercase">{game.tv}</span>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Scores */}
                                            <div className="p-6 space-y-4">
                                                <div className="space-y-3">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-lg font-black text-white uppercase">{game.away}</span>
                                                        <span className={cn(
                                                            "text-2xl font-black tabular-nums",
                                                            game.status === "PRE" ? "text-dash-text-muted" : "text-white"
                                                        )}>
                                                            {game.awayScore || 0}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-lg font-black text-white uppercase">{game.home}</span>
                                                        <span className={cn(
                                                            "text-2xl font-black tabular-nums",
                                                            game.status === "PRE" ? "text-dash-text-muted" : "text-white"
                                                        )}>
                                                            {game.homeScore || 0}
                                                        </span>
                                                    </div>
                                                </div>

                                                {/* Clock */}
                                                {(game.status === "LIVE" || game.status === "FINAL") && game.clock && (
                                                    <div className="flex items-center justify-center gap-2 py-2 bg-dash-bg-secondary rounded-xl">
                                                        <Clock className="w-3.5 h-3.5 text-gold" />
                                                        <span className="text-[10px] font-bold text-gold uppercase tracking-widest">
                                                            {game.clock}
                                                        </span>
                                                    </div>
                                                )}

                                                {/* AI Prediction */}
                                                {game.model_total && (
                                                    <div className="pt-4 border-t border-dash-border flex items-center justify-between">
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-7 h-7 bg-gold/10 rounded-lg flex items-center justify-center">
                                                                <Zap className="w-3.5 h-3.5 text-gold fill-current" />
                                                            </div>
                                                            <span className="text-[10px] font-bold text-dash-text-muted uppercase">AI Total</span>
                                                        </div>
                                                        <span className="text-sm font-black text-gold bg-gold/10 px-3 py-1 rounded-lg">
                                                            {game.model_total}
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                        </motion.div>
                                    ))
                                ) : (
                                    <div className="col-span-full py-20 text-center bg-dash-card border border-dash-border rounded-3xl">
                                        <div className="w-16 h-16 bg-dash-bg-secondary rounded-2xl flex items-center justify-center mx-auto mb-4">
                                            <Calendar className="w-8 h-8 text-dash-text-muted" />
                                        </div>
                                        <h3 className="text-xl font-black text-white uppercase mb-2">No Games Scheduled</h3>
                                        <p className="text-sm text-dash-text-muted max-w-sm mx-auto">
                                            Check back later or select a different date
                                        </p>
                                    </div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                </main>
            </div>

            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
    );
}
