"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
    Calendar,
    ChevronLeft,
    ChevronRight,
    Filter,
    Clock,
    TrendingUp,
    Zap,
    AlertCircle
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";
import { ConfidenceBadge } from "@/components/dashboard/ConfidenceBadge";
import { fetchScoreboard, fetchNBAScoreboard, formatDateForAPI, getCurrentETDate, type NCAAGame } from "@/lib/api";

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

const LEAGUES = ["All", "NBA", "NCAA"];

export default function ScoreboardPage() {
    const [selectedDate, setSelectedDate] = useState(getCurrentETDate());
    const [selectedLeague, setSelectedLeague] = useState("All");
    const [games, setGames] = useState<Game[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch games when date changes
    useEffect(() => {
        fetchGames();
    }, [selectedDate]);

    const fetchGames = async () => {
        setLoading(true);
        setError(null);

        try {
            const dateStr = formatDateForAPI(selectedDate);

            // Fetch both NBA and NCAA games in parallel
            const [ncaaData, nbaData] = await Promise.allSettled([
                fetchScoreboard('basketball-men', 'd1', dateStr),
                fetchNBAScoreboard(selectedDate)
            ]);

            const ncaaGames = ncaaData.status === 'fulfilled'
                ? transformNCAAGames(ncaaData.value.games || [], 'NCAA')
                : [];

            const nbaGames = nbaData.status === 'fulfilled'
                ? transformNCAAGames(nbaData.value.games || [], 'NBA')
                : [];

            setGames([...nbaGames, ...ncaaGames]);
        } catch (err) {
            console.error('Error fetching games:', err);
            setError('Failed to load games. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const transformNCAAGames = (ncaaGames: NCAAGame[], league: string = 'NCAA'): Game[] => {
        return ncaaGames.map((item) => {
            const game = item.game;
            const isLive = game.gameState === 'live';
            const isFinal = game.gameState === 'final';

            // Determine game status
            let status: 'scheduled' | 'live' | 'final' = 'scheduled';
            if (isLive) status = 'live';
            else if (isFinal) status = 'final';

            // Format time display
            let timeDisplay = game.startTime || '';
            if (isLive && game.currentPeriod) {
                timeDisplay = game.currentPeriod;
            } else if (isFinal) {
                timeDisplay = 'Final';
            }

            // Mock prediction data (TODO: integrate with prediction API)
            const mockTotal = 150;
            const mockEdge = Math.random() * 5 + 1;
            const mockConfidence: 'lock' | 'strong' | 'lean' =
                mockEdge > 4 ? 'lock' : mockEdge > 2.5 ? 'strong' : 'lean';

            return {
                id: game.gameID,
                league: league,
                status,
                time: timeDisplay,
                away: {
                    code: game.away.names.short,
                    name: game.away.names.full,
                    score: game.away.score
                },
                home: {
                    code: game.home.names.short,
                    name: game.home.names.full,
                    score: game.home.score
                },
                prediction: {
                    type: Math.random() > 0.5 ? 'OVER' : 'UNDER',
                    line: mockTotal,
                    pick: `${Math.random() > 0.5 ? 'OVER' : 'UNDER'} ${mockTotal}`,
                    edge: mockEdge,
                    confidence: mockConfidence
                }
            };
        });
    };

    const filteredGames = games.filter(game => {
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
                                <button
                                    onClick={() => {
                                        const newDate = new Date(selectedDate);
                                        newDate.setDate(newDate.getDate() - 1);
                                        setSelectedDate(newDate);
                                    }}
                                    className="p-2 hover:bg-dash-bg-secondary rounded-lg transition-colors"
                                >
                                    <ChevronLeft className="w-4 h-4 text-dash-text-muted" />
                                </button>
                                <span className="px-4 text-sm font-bold text-white">
                                    {selectedDate.toLocaleDateString('en-US', {
                                        month: 'short',
                                        day: 'numeric',
                                        year: selectedDate.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
                                    })}
                                </span>
                                <button
                                    onClick={() => {
                                        const newDate = new Date(selectedDate);
                                        newDate.setDate(newDate.getDate() + 1);
                                        setSelectedDate(newDate);
                                    }}
                                    className="p-2 hover:bg-dash-bg-secondary rounded-lg transition-colors"
                                >
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

                        {/* Loading State */}
                        {loading && (
                            <div className="flex items-center justify-center py-20">
                                <div className="text-center">
                                    <div className="w-12 h-12 border-4 border-gold border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                                    <p className="text-sm font-bold text-dash-text-muted uppercase tracking-wider">
                                        Loading games...
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Error State */}
                        {error && !loading && (
                            <div className="flex items-center justify-center py-20">
                                <div className="text-center max-w-md">
                                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                                    <p className="text-sm font-bold text-white mb-2">Error Loading Games</p>
                                    <p className="text-xs text-dash-text-muted mb-4">{error}</p>
                                    <button
                                        onClick={fetchGames}
                                        className="px-6 py-2 bg-gold text-dash-bg text-xs font-black uppercase tracking-widest rounded-xl hover:scale-105 transition-transform"
                                    >
                                        Try Again
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* No Games State */}
                        {!loading && !error && filteredGames.length === 0 && (
                            <div className="flex items-center justify-center py-20">
                                <div className="text-center">
                                    <Calendar className="w-12 h-12 text-dash-text-muted mx-auto mb-4" />
                                    <p className="text-sm font-bold text-white mb-2">No Games Found</p>
                                    <p className="text-xs text-dash-text-muted">
                                        No games scheduled for this date
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Live Games */}
                        {!loading && !error && liveGames.length > 0 && (
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
                        {!loading && !error && upcomingGames.length > 0 && (
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
                        {!loading && !error && finalGames.length > 0 && (
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

            <BottomNav />
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
