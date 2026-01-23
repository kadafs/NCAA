"use client";

import React, { useRef } from "react";
import { ChevronLeft, ChevronRight, Play } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import Link from "next/link";

/**
 * GameCarousel - Dark theme scoreboard carousel
 * 
 * Features:
 * - Horizontal scroll with snap points
 * - Arrow navigation on desktop
 * - Swipeable on mobile
 * - Dark theme matching reference design
 */

interface GameInfo {
    id: string;
    league: string;
    round: string;
    time: string;
    status: 'scheduled' | 'live' | 'final';
    away: { code: string; name: string; score?: number };
    home: { code: string; name: string; score?: number };
    edge?: number;
    prediction?: string;
}

const MOCK_GAMES: GameInfo[] = [
    {
        id: "1",
        league: "NBA",
        round: "Game 42",
        time: "7:30 PM ET",
        status: "scheduled",
        away: { code: "LAL", name: "Lakers" },
        home: { code: "BOS", name: "Celtics" },
        edge: 3.7,
        prediction: "OVER 234.5"
    },
    {
        id: "2",
        league: "NCAA",
        round: "Big 12",
        time: "9:00 PM ET",
        status: "live",
        away: { code: "DUKE", name: "Duke", score: 68 },
        home: { code: "UNC", name: "North Carolina", score: 71 },
        edge: 5.2,
        prediction: "UNC -4.5"
    },
    {
        id: "3",
        league: "EURO",
        round: "Round 20",
        time: "2:00 PM ET",
        status: "scheduled",
        away: { code: "REAL", name: "Real Madrid" },
        home: { code: "FENER", name: "Fenerbahce" },
        edge: 4.1,
        prediction: "UNDER 155.5"
    },
    {
        id: "4",
        league: "NBL",
        round: "Round 15",
        time: "4:00 AM ET",
        status: "scheduled",
        away: { code: "MEL", name: "Melbourne" },
        home: { code: "SYD", name: "Sydney" },
        edge: 2.8,
        prediction: "OVER 178.5"
    },
    {
        id: "5",
        league: "ACB",
        round: "Jornada 18",
        time: "3:30 PM ET",
        status: "scheduled",
        away: { code: "MAD", name: "Real Madrid" },
        home: { code: "BARCA", name: "Barcelona" },
        edge: 6.1,
        prediction: "BARCA -3.5"
    },
];

export function GameCarousel() {
    const scrollRef = useRef<HTMLDivElement>(null);

    const scroll = (direction: "left" | "right") => {
        if (scrollRef.current) {
            const { scrollLeft } = scrollRef.current;
            const scrollTo = direction === "left" ? scrollLeft - 300 : scrollLeft + 300;
            scrollRef.current.scrollTo({ left: scrollTo, behavior: "smooth" });
        }
    };

    return (
        <div className="relative group w-full py-6 bg-dash-bg-secondary border-y border-dash-border overflow-hidden">
            <div className="max-w-7xl mx-auto px-4 relative flex items-center">

                {/* Left Scroll Button */}
                <button
                    onClick={() => scroll("left")}
                    className="absolute left-2 z-10 w-10 h-10 bg-dash-card border border-dash-border hover:border-gold/30 rounded-full flex items-center justify-center text-dash-text-muted hover:text-white transition-all opacity-0 group-hover:opacity-100"
                    aria-label="Scroll left"
                >
                    <ChevronLeft className="w-5 h-5" />
                </button>

                {/* Carousel */}
                <div
                    ref={scrollRef}
                    className="flex gap-4 overflow-x-auto no-scrollbar scroll-smooth px-8 w-full snap-x"
                >
                    {MOCK_GAMES.map((game, i) => (
                        <motion.div
                            key={game.id}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="flex-shrink-0 snap-start"
                        >
                            <Link
                                href={`/dashboard/${game.league.toLowerCase()}`}
                                className="block w-[220px] bg-dash-card border border-dash-border rounded-2xl overflow-hidden hover:border-gold/30 transition-all group/card"
                            >
                                {/* Header */}
                                <div className="bg-dash-bg px-3 py-2 border-b border-dash-border flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        {game.status === 'live' && (
                                            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                                        )}
                                        <span className="text-[9px] font-black uppercase tracking-widest text-gold">
                                            {game.league}
                                        </span>
                                    </div>
                                    <span className="text-[9px] font-bold text-dash-text-muted uppercase">
                                        {game.round}
                                    </span>
                                </div>

                                {/* Content */}
                                <div className="p-4 space-y-3">
                                    {/* Time */}
                                    <div className="text-[10px] font-bold text-dash-text-muted flex items-center gap-1.5 uppercase">
                                        <span className={cn(
                                            "w-1.5 h-1.5 rounded-full",
                                            game.status === 'live' ? "bg-red-500" : "bg-gold"
                                        )} />
                                        {game.status === 'live' ? 'LIVE' : game.time}
                                    </div>

                                    {/* Teams */}
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm font-black text-white">{game.away.code}</span>
                                            <span className="text-sm font-bold text-dash-text-muted">
                                                {game.away.score ?? '-'}
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm font-black text-white">{game.home.code}</span>
                                            <span className="text-sm font-bold text-dash-text-muted">
                                                {game.home.score ?? '-'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Prediction & Edge */}
                                    {game.prediction && (
                                        <div className="pt-3 border-t border-dash-border flex items-center justify-between">
                                            <span className="text-[9px] font-bold text-dash-text-muted uppercase truncate max-w-[120px]">
                                                {game.prediction}
                                            </span>
                                            <span className={cn(
                                                "text-[10px] font-black px-2 py-0.5 rounded",
                                                game.edge && game.edge > 4 ? "bg-gold/10 text-gold" : "bg-cyan/10 text-cyan"
                                            )}>
                                                +{game.edge?.toFixed(1)}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            </Link>
                        </motion.div>
                    ))}

                    {/* View All Button */}
                    <div className="flex-shrink-0 flex items-center px-6 snap-start">
                        <Link
                            href="/scoreboard"
                            className="flex flex-col items-center gap-2 group/btn"
                        >
                            <div className="w-12 h-12 rounded-full border border-dash-border flex items-center justify-center group-hover/btn:border-gold group-hover/btn:bg-gold/10 transition-all">
                                <Play className="w-5 h-5 text-gold fill-gold" />
                            </div>
                            <span className="text-[9px] font-bold text-dash-text-muted uppercase tracking-widest group-hover/btn:text-gold transition-colors">
                                View all
                            </span>
                        </Link>
                    </div>
                </div>

                {/* Right Scroll Button */}
                <button
                    onClick={() => scroll("right")}
                    className="absolute right-2 z-10 w-10 h-10 bg-dash-card border border-dash-border hover:border-gold/30 rounded-full flex items-center justify-center text-dash-text-muted hover:text-white transition-all opacity-0 group-hover:opacity-100"
                    aria-label="Scroll right"
                >
                    <ChevronRight className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}
