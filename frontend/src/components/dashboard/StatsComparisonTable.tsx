"use client";

import React from "react";
import { motion } from "framer-motion";
import { PlayerAdvancedStats } from "@/types";

interface StatsComparisonTableProps {
    player1Stats: PlayerAdvancedStats;
    player2Stats: PlayerAdvancedStats;
    player1Name?: string;
    player2Name?: string;
}

/**
 * StatsComparisonTable - Side-by-side advanced stats comparison
 * 
 * Displays player advanced stats in a two-column layout matching reference:
 * - Ast Ratio, Reb %, eFG %, TS %, Usg %, Oreb %, Dreb %
 * - Better values are subtly highlighted
 * 
 * Mobile: Maintains two columns but reduces font size
 */
export function StatsComparisonTable({
    player1Stats,
    player2Stats,
    player1Name = "Player 1",
    player2Name = "Player 2"
}: StatsComparisonTableProps) {

    const statRows = [
        { key: "astRatio", label: "Ast Ratio", p1: player1Stats.astRatio, p2: player2Stats.astRatio },
        { key: "rebPct", label: "Reb %", p1: player1Stats.rebPct, p2: player2Stats.rebPct },
        { key: "efgPct", label: "Efg %", p1: player1Stats.efgPct, p2: player2Stats.efgPct },
        { key: "tsPct", label: "Ts %", p1: player1Stats.tsPct, p2: player2Stats.tsPct },
        { key: "usgPct", label: "Usg %", p1: player1Stats.usgPct, p2: player2Stats.usgPct },
        { key: "orebPct", label: "Oreb %", p1: player1Stats.orebPct, p2: player2Stats.orebPct },
        { key: "drebPct", label: "Dreb %", p1: player1Stats.drebPct, p2: player2Stats.drebPct },
    ];

    return (
        <div className="bg-dash-card border border-dash-border rounded-3xl p-4 md:p-6">
            {/* Header */}
            <div className="grid grid-cols-3 gap-2 mb-4 pb-3 border-b border-dash-border">
                <div className="text-[10px] font-bold text-dash-text-muted uppercase text-center md:text-left" />
                <div className="text-[10px] font-bold text-gold uppercase text-center">
                    {player1Name.split(' ').pop()}
                </div>
                <div className="text-[10px] font-bold text-cyan uppercase text-center">
                    {player2Name.split(' ').pop()}
                </div>
            </div>

            {/* Stat Rows */}
            <div className="space-y-3">
                {statRows.map((row, idx) => {
                    const p1Better = row.p1 > row.p2;
                    const p2Better = row.p2 > row.p1;

                    return (
                        <motion.div
                            key={row.key}
                            className="grid grid-cols-3 gap-2 items-center"
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.05 }}
                        >
                            {/* Label */}
                            <div className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase">
                                {row.label}
                            </div>

                            {/* Player 1 Value */}
                            <div className={`text-xs md:text-sm font-bold text-center ${p1Better ? "text-gold" : "text-dash-text-secondary"
                                }`}>
                                {row.p1.toFixed(1)}
                            </div>

                            {/* Player 2 Value */}
                            <div className={`text-xs md:text-sm font-bold text-center ${p2Better ? "text-cyan" : "text-dash-text-secondary"
                                }`}>
                                {row.p2.toFixed(1)}
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
