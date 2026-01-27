"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
    Calendar,
    ChevronLeft,
    ChevronRight,
    Filter,
    Clock,
    TrendingUp,
    Zap
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";
import { ConfidenceBadge } from "@/components/dashboard/ConfidenceBadge";

/**
 * Scoreboard Page - All games across leagues
 * 
 * Features:
 * - Date navigation
 * - League filtering
 * - Game cards with predictions
 * - Live score updates
 */

interface Game {
    id: string;
    league: string;
    status: 'scheduled' | 'live' | 'final';
    time: string;
    away: { code: string; name: string; logo?: string; score?: number };
    home: { code: string; name: string; logo?: string; score?: number };
    prediction: {
        type: 'OVER' | 'UNDER' | 'SPREAD';
        line: number;
        pick: string;
        edge: number;
        confidence: 'lock' | 'strong' | 'lean';
    };
}

const MOCK_GAMES: Game[] = [
    {
        id: "1",
        league: "NBA",
        status: "live",
        time: "Q4 2:34",
        away: { code: "LAL", name: "Lakers", score: 102 },
        home: { code: "BOS", name: "Celtics", score: 108 },
        prediction: { type: "OVER", line: 234.5, pick: "OVER 234.5", edge: 3.7, confidence: "strong" }
    },
    {
        id: "2",
        league: "NBA",
        status: "scheduled",
        time: "7:30 PM",
        away: { code: "MIA", name: "Heat" },
        home: { code: "NYK", name: "Knicks" },
        prediction: { type: "UNDER", line: 215.0, pick: "UNDER 215.0", edge: 4.4, confidence: "lock" }
    },
    {
        id: "3",
        league: "NCAA",
        status: "live",
        time: "2H 8:45",
        away: { code: "DUKE", name: "Duke", score: 68 },
        home: { code: "UNC", name: "North Carolina", score: 71 },
        prediction: { type: "SPREAD", line: -4.5, pick: "UNC -4.5", edge: 5.2, confidence: "strong" }
    },
];

const LEAGUES = ["All", "NBA", "NCAA"];

export default function ScoreboardPage() {
    const [activeTab, setActiveTab] = useState("live");
    const [selectedDate, setSelectedDate] = useState(new Date());
    const [selectedLeague, setSelectedLeague] = useState("All");

    const filteredGames = MOCK_GAMES.filter(game => {
        if (selectedLeague !== "All" && game.league !== selectedLeague) return false;
        return true;
    });

    const liveGames = filteredGames.filter(g => g.status === 'live');
    const upcomingGames = filteredGames.filter(g => g.status === 'scheduled');
    const finalGames = filteredGames.filter(g => g.status === 'final');

    return (
        <div className="min-h-screen bg-dash-bg text-dash-text-primary">
            <LeftSidebar />

            <div className="lg:ml-16 xl:ml-20">
                {/* Header */}
                <header className="sticky top-0 z-30 bg-dash-bg/80 backdrop-blur-xl border-b border-dash-border">
                    <div className="px-4 py-4 md:px-6 lg:px-8">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div>
                                <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tighter flex items-center gap-3">
                                    <Calendar className="w-7 h-7 text-gold" />
                                    Score<span className="text-gold italic">board</span>
                                </h1>
                                <p className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase tracking-widest mt-1">
                                    All Games • {filteredGames.length} Active
                                </p>
                            </div>

                            {/* Date Navigation */}
                            <div className="flex items-center gap-2 bg-dash-card border border-dash-border rounded-xl p-1">
                                <button className="p-2 hover:bg-dash-bg-secondary rounded-lg transition-colors">
                                    <ChevronLeft className="w-4 h-4 text-dash-text-muted" />
                                </button>
                                <span className="px-4 text-sm font-bold text-white">
                                    Today, Jan 22
                                </span>
                                <button className="p-2 hover:bg-dash-bg-secondary rounded-lg transition-colors">
                                    <ChevronRight className="w-4 h-4 text-dash-text-muted" />
                                </button>
                            </div>
                        </div>

                        {/* League Filter */}
                        <div className="flex items-center gap-2 mt-4 overflow-x-auto no-scrollbar">
                            {LEAGUES.map((league) => (
                                <button
                                    key={league}
                                    onClick={() => setSelectedLeague(league)}
                                    className={cn(
                                        "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all whitespace-nowrap",
                                        selectedLeague === league
                                            ? "bg-gold text-dash-bg"
                                            : "bg-dash-bg-secondary border border-dash-border text-dash-text-muted hover:text-white"
                                    )}
                                >
                                    {league}
                                </button>
                            ))}
                        </div>
                    </div>
                </header>

                {/* Content */}
                <main className="p-4 md:p-6 lg:p-8 pb-24 lg:pb-8">
                    <div className="max-w-[1400px] mx-auto space-y-8">

                        {/* Live Games */}
                        {liveGames.length > 0 && (
                            <section>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                                    <h2 className="text-sm font-black text-white uppercase tracking-wider">
                                        Live Now
                                    </h2>
                                    <span className="text-[10px] font-bold text-dash-text-muted">
                                        {liveGames.length} games
                                    </span>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {liveGames.map((game, idx) => (
                                        <GameCard key={game.id} game={game} index={idx} />
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* Upcoming Games */}
                        {upcomingGames.length > 0 && (
                            <section>
                                <div className="flex items-center gap-3 mb-4">
                                    <Clock className="w-4 h-4 text-gold" />
                                    <h2 className="text-sm font-black text-white uppercase tracking-wider">
                                        Upcoming
                                    </h2>
                                    <span className="text-[10px] font-bold text-dash-text-muted">
                                        {upcomingGames.length} games
                                    </span>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {upcomingGames.map((game, idx) => (
                                        <GameCard key={game.id} game={game} index={idx} />
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* Final Games */}
                        {finalGames.length > 0 && (
                            <section>
                                <div className="flex items-center gap-3 mb-4">
                                    <TrendingUp className="w-4 h-4 text-dash-text-muted" />
                                    <h2 className="text-sm font-black text-dash-text-muted uppercase tracking-wider">
                                        Completed
                                    </h2>
                                    <span className="text-[10px] font-bold text-dash-text-muted">
                                        {finalGames.length} games
                                    </span>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {finalGames.map((game, idx) => (
                                        <GameCard key={game.id} game={game} index={idx} />
                                    ))}
                                </div>
                            </section>
                        )}
                    </div>
                </main>
            </div>

            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
    );
}

interface GameCardProps {
    game: Game;
    index: number;
}

function GameCard({ game, index }: GameCardProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="bg-dash-card border border-dash-border rounded-2xl overflow-hidden hover:border-gold/30 transition-all group"
        >
            {/* Header */}
            <div className="px-4 py-3 bg-dash-bg border-b border-dash-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {game.status === 'live' && (
                        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                    )}
                    <span className="text-[10px] font-black text-gold uppercase">{game.league}</span>
                </div>
                <span className={cn(
                    "text-[10px] font-bold uppercase",
                    game.status === 'live' ? "text-red-400" :
                        game.status === 'final' ? "text-dash-text-muted" : "text-white"
                )}>
                    {game.time}
                </span>
            </div>

            {/* Teams */}
            <div className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-dash-bg-secondary rounded-lg flex items-center justify-center text-[10px] font-black text-white">
                            {game.away.code[0]}
                        </div>
                        <span className="text-sm font-black text-white">{game.away.code}</span>
                    </div>
                    <span className="text-lg font-black text-white">
                        {game.away.score ?? '-'}
                    </span>
                </div>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-dash-bg-secondary rounded-lg flex items-center justify-center text-[10px] font-black text-white">
                            {game.home.code[0]}
                        </div>
                        <span className="text-sm font-black text-white">{game.home.code}</span>
                    </div>
                    <span className="text-lg font-black text-white">
                        {game.home.score ?? '-'}
                    </span>
                </div>
            </div>

            {/* Prediction Footer */}
            <div className="px-4 py-3 bg-dash-bg-secondary border-t border-dash-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <ConfidenceBadge confidence={game.prediction.confidence} />
                    <span className="text-xs font-bold text-white">{game.prediction.pick}</span>
                </div>
                <div className={cn(
                    "text-[10px] font-black px-2 py-1 rounded",
                    game.prediction.edge > 4 ? "bg-gold/10 text-gold" : "bg-cyan/10 text-cyan"
                )}>
                    +{game.prediction.edge.toFixed(1)}
                </div>
            </div>
        </motion.div>
    );
}
