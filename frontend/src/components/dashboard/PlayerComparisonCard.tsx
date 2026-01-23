"use client";

import React from "react";
import { motion } from "framer-motion";
import { Player } from "@/types";
import { ChevronDown } from "lucide-react";

interface PlayerComparisonCardProps {
    player1: Player;
    player2: Player;
}

/**
 * PlayerComparisonCard - Main VS layout component
 * 
 * Displays two players side-by-side with:
 * - Player photos with team badges
 * - Jersey number and position
 * - Physical attributes (Height, Weight, Experience)
 * - Quick stats row (Pts, Reb, Ast, PIE)
 * 
 * Mobile: Stacks vertically with VS badge in between
 * Desktop: Side-by-side horizontal layout
 */
export function PlayerComparisonCard({ player1, player2 }: PlayerComparisonCardProps) {
    return (
        <div className="bg-dash-card border border-dash-border rounded-3xl p-4 md:p-6 lg:p-8">
            {/* Main VS Container */}
            <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8">

                {/* Player 1 */}
                <PlayerProfile player={player1} accentColor="gold" />

                {/* VS Badge */}
                <div className="flex-shrink-0 text-xl md:text-2xl font-black text-dash-text-muted italic tracking-tighter">
                    VS
                </div>

                {/* Player 2 */}
                <PlayerProfile player={player2} accentColor="cyan" />
            </div>

            {/* Divider */}
            <div className="h-px bg-dash-border my-6" />

            {/* Physical Attributes Comparison */}
            <div className="grid grid-cols-2 gap-4 md:gap-8">
                <PlayerAttributes player={player1} />
                <PlayerAttributes player={player2} />
            </div>

            {/* Divider */}
            <div className="h-px bg-dash-border my-6" />

            {/* Quick Stats Row */}
            <div className="grid grid-cols-2 gap-4 md:gap-8">
                <QuickStats player={player1} accentColor="gold" />
                <QuickStats player={player2} accentColor="cyan" />
            </div>
        </div>
    );
}

interface PlayerProfileProps {
    player: Player;
    accentColor: "gold" | "cyan";
}

function PlayerProfile({ player, accentColor }: PlayerProfileProps) {
    const borderColor = accentColor === "gold" ? "border-gold" : "border-cyan";
    const textColor = accentColor === "gold" ? "text-gold" : "text-cyan";
    const bgGlow = accentColor === "gold"
        ? "shadow-[0_0_30px_rgba(251,191,36,0.15)]"
        : "shadow-[0_0_30px_rgba(6,182,212,0.15)]";

    return (
        <motion.div
            className="flex flex-col items-center text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            {/* Player Image Container */}
            <div className={`relative w-24 h-24 md:w-32 md:h-32 lg:w-40 lg:h-40 rounded-2xl overflow-hidden ${bgGlow}`}>
                <img
                    src={player.image}
                    alt={player.name}
                    className="w-full h-full object-cover object-top"
                />
                {/* Gradient overlay for better text visibility */}
                <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/80 to-transparent" />
            </div>

            {/* Name with accent indicator */}
            <div className="mt-3 flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${accentColor === "gold" ? "bg-gold" : "bg-cyan"}`} />
                <span className="text-sm md:text-base font-bold text-white truncate max-w-[140px] md:max-w-[180px]">
                    {player.name}
                </span>
                <ChevronDown className="w-4 h-4 text-dash-text-muted" />
            </div>

            {/* Team Badge + Number + Position */}
            <div className="mt-2 flex items-center gap-2">
                <img
                    src={player.teamLogo}
                    alt={player.teamCode}
                    className="w-5 h-5 md:w-6 md:h-6 object-contain"
                />
                <span className={`text-xs font-bold ${textColor}`}>#{player.number}</span>
                <span className="text-xs font-medium text-dash-text-muted">{player.position}</span>
            </div>
        </motion.div>
    );
}

interface PlayerAttributesProps {
    player: Player;
}

function PlayerAttributes({ player }: PlayerAttributesProps) {
    const attributes = [
        { label: "Height", value: player.height },
        { label: "Weight", value: player.weight },
        { label: "Experience", value: player.experience },
    ];

    return (
        <div className="space-y-2">
            {attributes.map((attr) => (
                <div key={attr.label} className="flex items-center gap-4">
                    <span className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase w-20 md:w-24">
                        {attr.label}
                    </span>
                    <span className="text-xs md:text-sm font-bold text-white">
                        {attr.value}
                    </span>
                </div>
            ))}
        </div>
    );
}

interface QuickStatsProps {
    player: Player;
    accentColor: "gold" | "cyan";
}

function QuickStats({ player, accentColor }: QuickStatsProps) {
    const bgColor = accentColor === "gold" ? "bg-gold/10" : "bg-cyan/10";
    const borderColor = accentColor === "gold" ? "border-gold/20" : "border-cyan/20";
    const textColor = accentColor === "gold" ? "text-gold" : "text-cyan";

    const stats = [
        { label: "Pts", value: player.ppg },
        { label: "Reb", value: player.rpg },
        { label: "Ast", value: player.apg },
        { label: "Pie", value: player.pie },
    ];

    return (
        <div className="flex justify-between gap-2">
            {stats.map((stat) => (
                <div
                    key={stat.label}
                    className={`flex-1 ${bgColor} border ${borderColor} rounded-xl p-2 md:p-3 text-center`}
                >
                    <div className={`text-[10px] font-bold uppercase ${textColor}`}>
                        {stat.label}
                    </div>
                    <div className="text-sm md:text-lg font-black text-white mt-0.5">
                        {stat.value.toFixed(1)}
                    </div>
                </div>
            ))}
        </div>
    );
}
