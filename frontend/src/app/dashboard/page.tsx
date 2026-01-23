"use client";

import React, { useState, Suspense } from "react";
import { motion } from "framer-motion";
import { Search, Bell, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

// Types
import { Player, PlayerComparison, PlayerAdvancedStats } from "@/types";

// Components
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";
import { PlayerComparisonCard } from "@/components/dashboard/PlayerComparisonCard";
import { StatsComparisonTable } from "@/components/dashboard/StatsComparisonTable";
import { HorizontalBarChart } from "@/components/dashboard/HorizontalBarChart";
import { CircularGauge } from "@/components/dashboard/CircularGauge";
import { ForecastLineChart } from "@/components/dashboard/ForecastLineChart";

// --- MOCK DATA ---
const MOCK_PLAYER_1: Player = {
    id: "lebron",
    name: "LeBron James",
    team: "Lakers",
    teamCode: "LAL",
    teamLogo: "https://a.espncdn.com/i/teamlogos/nba/500/lal.png",
    number: 23,
    position: "Forward",
    image: "https://a.espncdn.com/i/headshots/nba/players/full/1966.png",
    height: "6ft 9in",
    weight: "250 lbs",
    experience: "16 yrs",
    ppg: 25.4,
    rpg: 7.0,
    apg: 10.8,
    pie: 19.8,
    netRating: 59.8,
    advancedStats: {
        astRatio: 29.3,
        rebPct: 29.5,
        efgPct: 79.2,
        tsPct: 39.7,
        usgPct: 59.3,
        orebPct: 64.8,
        drebPct: 44.2,
    }
};

const MOCK_PLAYER_2: Player = {
    id: "marcus",
    name: "Marcus Morris Sr.",
    team: "Knicks",
    teamCode: "NYK",
    teamLogo: "https://a.espncdn.com/i/teamlogos/nba/500/nyk.png",
    number: 13,
    position: "Forward",
    image: "https://a.espncdn.com/i/headshots/nba/players/full/6462.png",
    height: "6ft 8in",
    weight: "218 lbs",
    experience: "8 yrs",
    ppg: 18.4,
    rpg: 6.0,
    apg: 10.3,
    pie: 10.4,
    netRating: 65.4,
    advancedStats: {
        astRatio: 32.5,
        rebPct: 27.4,
        efgPct: 83.9,
        tsPct: 29.7,
        usgPct: 61.8,
        orebPct: 42.1,
        drebPct: 51.9,
    }
};

const MOCK_COMPARISON_BARS = [
    { label: "Points from 2-Point Makes", labelShort: "Pts 2Pt Mr", player1Value: 12.1, player2Value: 8.4, player1Pct: 27.1, player2Pct: 35.3 },
    { label: "Points from 3-Point Makes", labelShort: "Pts 3Pt Mr", player1Value: 8.5, player2Value: 6.2, player1Pct: 57.5, player2Pct: 46.0 },
    { label: "Points from Putbacks", labelShort: "Pts Pb", player1Value: 2.1, player2Value: 1.8, player1Pct: 29.0, player2Pct: 37.9 },
    { label: "Points from Free Throws", labelShort: "Pts Ft", player1Value: 4.8, player2Value: 3.2, player1Pct: 68.9, player2Pct: 77.5 },
];

const MOCK_FORECAST_DATA = [
    { time: "Q1", awayVal: 45, homeVal: 52 },
    { time: "Q2", awayVal: 52, homeVal: 48 },
    { time: "Q3", awayVal: 58, homeVal: 55 },
    { time: "Q4", awayVal: 55, homeVal: 62 },
    { time: "OT", awayVal: 60, homeVal: 65 },
];

/**
 * Dashboard - Main analytics dashboard matching reference design
 * 
 * Layout Structure:
 * - Left sidebar: Icon navigation (desktop only)
 * - Main content: Player comparison, stats, charts
 * - Right section: Gauges and forecast
 * - Bottom nav: Mobile navigation
 * 
 * Mobile-first responsive design with:
 * - Single column on mobile
 * - Two columns on tablet
 * - Full layout on desktop
 */
export default function Dashboard() {
    const [activeTab, setActiveTab] = useState("home");
    const [searchQuery, setSearchQuery] = useState("");

    return (
        <div className="min-h-screen bg-dash-bg text-dash-text-primary">
            {/* Left Sidebar - Desktop Only */}
            <LeftSidebar />

            {/* Main Content Area - offset for sidebar on desktop */}
            <div className="lg:ml-16 xl:ml-20">
                {/* Top Header Bar */}
                <header className="sticky top-0 z-30 bg-dash-bg/80 backdrop-blur-xl border-b border-dash-border">
                    <div className="flex items-center justify-between px-4 py-3 md:px-6 lg:px-8">
                        {/* Search Bar */}
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dash-text-muted" />
                            <input
                                type="text"
                                placeholder="Search for a Player or Team"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full bg-dash-bg-secondary border border-dash-border rounded-xl py-2.5 pl-10 pr-4 text-xs font-medium text-white placeholder:text-dash-text-muted focus:outline-none focus:border-gold/50 transition-colors"
                            />
                        </div>

                        {/* Right Actions */}
                        <div className="flex items-center gap-3 ml-4">
                            <button
                                className="w-10 h-10 rounded-xl bg-dash-card border border-dash-border flex items-center justify-center hover:border-gold/30 transition-colors"
                                aria-label="Notifications"
                            >
                                <Bell className="w-4 h-4 text-dash-text-muted" />
                            </button>
                            <div className="w-10 h-10 rounded-full bg-gold/10 border border-gold/20 flex items-center justify-center">
                                <Trophy className="w-5 h-5 text-gold" />
                            </div>
                        </div>
                    </div>
                </header>

                {/* Main Dashboard Content */}
                <main className="p-4 md:p-6 lg:p-8 pb-24 lg:pb-8">
                    <div className="max-w-[1600px] mx-auto">
                        {/* Main Grid Layout */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">

                            {/* Left Column: Player Comparison + Horizontal Bars */}
                            <div className="lg:col-span-7 space-y-6">
                                {/* Player VS Card */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                >
                                    <PlayerComparisonCard
                                        player1={MOCK_PLAYER_1}
                                        player2={MOCK_PLAYER_2}
                                    />
                                </motion.div>

                                {/* Horizontal Bar Charts */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: 0.1 }}
                                >
                                    <HorizontalBarChart data={MOCK_COMPARISON_BARS} />
                                </motion.div>
                            </div>

                            {/* Right Column: Gauges + Stats + Forecast */}
                            <div className="lg:col-span-5 space-y-6">
                                {/* Circular Gauges Row */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: 0.15 }}
                                    className="bg-dash-card border border-dash-border rounded-3xl p-4 md:p-6"
                                >
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="flex justify-center">
                                            <CircularGauge
                                                value={MOCK_PLAYER_1.netRating}
                                                label="Net Rating"
                                                color="#FBBF24"
                                                size={120}
                                            />
                                        </div>
                                        <div className="flex justify-center">
                                            <CircularGauge
                                                value={MOCK_PLAYER_2.netRating}
                                                label="Net Rating"
                                                color="#06B6D4"
                                                size={120}
                                            />
                                        </div>
                                    </div>
                                </motion.div>

                                {/* Stats Comparison Table */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: 0.2 }}
                                >
                                    <StatsComparisonTable
                                        player1Stats={MOCK_PLAYER_1.advancedStats}
                                        player2Stats={MOCK_PLAYER_2.advancedStats}
                                        player1Name={MOCK_PLAYER_1.name}
                                        player2Name={MOCK_PLAYER_2.name}
                                    />
                                </motion.div>

                                {/* Forecast Chart */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: 0.25 }}
                                    className="bg-dash-card border border-dash-border rounded-3xl p-4 md:p-6"
                                >
                                    <div className="mb-4">
                                        <h3 className="text-sm font-bold text-white">Forecasts</h3>
                                        <p className="text-[10px] text-dash-text-muted mt-0.5">
                                            Projected performance trends
                                        </p>
                                    </div>
                                    <ForecastLineChart
                                        data={MOCK_FORECAST_DATA}
                                        height={180}
                                        awayLabel={MOCK_PLAYER_1.name}
                                        homeLabel={MOCK_PLAYER_2.name}
                                    />
                                </motion.div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>

            {/* Bottom Navigation - Mobile Only */}
            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
    );
}
