"use client";

import React from "react";
import { motion } from "framer-motion";

interface BarData {
    label: string;
    labelShort: string;
    player1Value: number;
    player2Value: number;
    player1Pct: number;
    player2Pct: number;
}

interface HorizontalBarChartProps {
    data: BarData[];
    player1Color?: string;
    player2Color?: string;
}

/**
 * HorizontalBarChart - Comparative horizontal bar visualization
 * 
 * Displays dual-color percentage bars matching the reference design:
 * - Category labels on left (Pts 2Pt Mr, Pts 3Pt Mr, Pts Pb, Pts Ft)
 * - Dual color bars (gold for player1, cyan for player2)
 * - Percentage values on right side
 * - Smooth animations with framer-motion
 * 
 * Mobile: Full width bars, slightly smaller labels
 */
export function HorizontalBarChart({
    data,
    player1Color = "#FBBF24",
    player2Color = "#06B6D4"
}: HorizontalBarChartProps) {
    return (
        <div className="bg-dash-card border border-dash-border rounded-3xl p-4 md:p-6">
            <div className="space-y-4">
                {data.map((item, idx) => (
                    <motion.div
                        key={item.label}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="space-y-2"
                    >
                        {/* Label Row */}
                        <div className="flex items-center justify-between">
                            <div className="flex flex-col">
                                <span className="text-xs font-bold text-white">
                                    {item.labelShort}
                                </span>
                                <span className="text-[8px] font-medium text-dash-text-muted uppercase hidden md:block">
                                    {item.label}
                                </span>
                            </div>
                            <div className="flex items-center gap-4 text-[10px] md:text-xs font-bold">
                                <span className="text-gold">{item.player1Pct.toFixed(1)}%</span>
                                <span className="text-cyan">{item.player2Pct.toFixed(1)}%</span>
                            </div>
                        </div>

                        {/* Bar Container */}
                        <div className="flex gap-1 h-3 md:h-4">
                            {/* Player 1 Bar */}
                            <motion.div
                                className="rounded-l-full"
                                style={{ backgroundColor: player1Color }}
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.min(item.player1Pct, 100)}%` }}
                                transition={{ duration: 0.8, ease: "easeOut", delay: idx * 0.1 }}
                            />
                            {/* Player 2 Bar */}
                            <motion.div
                                className="rounded-r-full"
                                style={{ backgroundColor: player2Color }}
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.min(item.player2Pct, 100)}%` }}
                                transition={{ duration: 0.8, ease: "easeOut", delay: idx * 0.1 + 0.1 }}
                            />
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}

/**
 * SingleHorizontalBar - Simple single-value horizontal bar
 * Used for individual stat displays
 */
interface SingleBarProps {
    label: string;
    value: number;
    maxValue?: number;
    color?: string;
}

export function SingleHorizontalBar({
    label,
    value,
    maxValue = 100,
    color = "#FBBF24"
}: SingleBarProps) {
    const percentage = Math.min((value / maxValue) * 100, 100);

    return (
        <div className="space-y-1">
            <div className="flex items-center justify-between text-[10px] font-bold">
                <span className="text-dash-text-muted uppercase">{label}</span>
                <span className="text-white">{value.toFixed(1)}</span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                />
            </div>
        </div>
    );
}
