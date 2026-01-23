"use client";

import React from "react";
import { motion } from "framer-motion";
import { Prediction } from "@/types";
import { cn } from "@/lib/utils";

interface ScoreboardCarouselProps {
    games: Prediction[];
}

export function ScoreboardCarousel({ games }: ScoreboardCarouselProps) {
    return (
        <div className="w-full bg-dash-bg-secondary border-b border-dash-border overflow-hidden">
            <div className="max-w-[1600px] mx-auto">
                <div className="flex overflow-x-auto no-scrollbar py-3 px-4 gap-4 snap-x">
                    {games.map((game) => (
                        <motion.div
                            key={game.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            whileHover={{ y: -2 }}
                            className="flex-shrink-0 w-[240px] bg-dash-card border border-dash-border rounded-xl p-3 snap-start relative group cursor-pointer"
                        >
                            {/* League Badge */}
                            <div className="absolute top-0 right-0 px-2 py-0.5 bg-dash-bg-secondary border-l border-b border-dash-border rounded-bl-lg text-[8px] font-black uppercase text-dash-text-muted group-hover:text-gold transition-colors">
                                {game.league}
                            </div>

                            <div className="flex flex-col gap-2">
                                <div className="flex justify-between items-center text-[10px] font-bold text-dash-text-muted uppercase">
                                    <span>{game.time}</span>
                                    <span className={cn(
                                        "text-[9px] px-1.5 rounded bg-dash-bg-secondary",
                                        game.edge > 5 ? "text-gold" : "text-cyan"
                                    )}>
                                        {game.marketTotal} O/U
                                    </span>
                                </div>

                                <div className="space-y-1">
                                    <div className="flex justify-between items-center text-xs font-bold text-dash-text-primary">
                                        <span>{game.awayTeam.code}</span>
                                        <span className="text-dash-text-muted">@</span>
                                        <span>{game.homeTeam.code}</span>
                                    </div>
                                    <div className="flex justify-center">
                                        <div className="h-0.5 w-12 bg-gradient-to-r from-transparent via-dash-border to-transparent" />
                                    </div>
                                </div>

                                <div className="flex justify-between items-end">
                                    <div className="flex flex-col">
                                        <span className="text-[8px] font-bold text-dash-text-muted uppercase">Model Result</span>
                                        <span className="text-sm font-black text-white italic">
                                            {game.modelTotal}
                                        </span>
                                    </div>
                                    <div className="text-right">
                                        <div className={cn(
                                            "text-[10px] font-black px-2 py-0.5 rounded-md inline-block",
                                            game.edge > 3 ? "bg-gold/10 text-gold" : "bg-cyan/10 text-cyan"
                                        )}>
                                            {game.edge > 0 ? "+" : ""}{game.edge.toFixed(1)} EDGE
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </div>
    );
}
