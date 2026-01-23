"use client";

import React, { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Search,
    User,
    Users,
    Trophy,
    ChevronRight,
    X,
    ArrowLeftRight,
    TrendingUp,
    Target,
    BarChart3,
    Zap
} from "lucide-react";
import { cn } from "@/lib/utils";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";

/**
 * Profile Page - Player & Team Search + Comparison
 * 
 * Features:
 * - Search players by name across all leagues
 * - Browse teams by league
 * - Head-to-head player comparison
 * - Head-to-head team comparison
 * - Stats visualization
 */

// Mock data - in production, fetch from API/Supabase
const MOCK_PLAYERS = [
    { id: "1", name: "LeBron James", team: "LAL", league: "nba", position: "SF", image: "https://a.espncdn.com/i/headshots/nba/players/full/1966.png", stats: { pts: 25.4, reb: 7.0, ast: 8.1, fg: 52.2, ts: 62.4 } },
    { id: "2", name: "Stephen Curry", team: "GSW", league: "nba", position: "PG", image: "https://a.espncdn.com/i/headshots/nba/players/full/3975.png", stats: { pts: 27.2, reb: 4.5, ast: 5.1, fg: 45.8, ts: 65.1 } },
    { id: "3", name: "Jayson Tatum", team: "BOS", league: "nba", position: "SF", image: "https://a.espncdn.com/i/headshots/nba/players/full/4065648.png", stats: { pts: 26.9, reb: 8.1, ast: 4.4, fg: 47.1, ts: 60.8 } },
    { id: "4", name: "Giannis Antetokounmpo", team: "MIL", league: "nba", position: "PF", image: "https://a.espncdn.com/i/headshots/nba/players/full/3032977.png", stats: { pts: 31.2, reb: 11.8, ast: 5.7, fg: 61.1, ts: 64.2 } },
    { id: "5", name: "Luka Doncic", team: "DAL", league: "nba", position: "PG", image: "https://a.espncdn.com/i/headshots/nba/players/full/3945274.png", stats: { pts: 33.1, reb: 9.2, ast: 9.8, fg: 48.7, ts: 58.9 } },
    { id: "6", name: "Kevin Durant", team: "PHX", league: "nba", position: "SF", image: "https://a.espncdn.com/i/headshots/nba/players/full/3202.png", stats: { pts: 29.1, reb: 6.7, ast: 5.0, fg: 52.5, ts: 66.2 } },
    { id: "7", name: "Nikola Jokic", team: "DEN", league: "nba", position: "C", image: "https://a.espncdn.com/i/headshots/nba/players/full/3112335.png", stats: { pts: 26.4, reb: 12.4, ast: 9.0, fg: 58.3, ts: 70.1 } },
    { id: "8", name: "Joel Embiid", team: "PHI", league: "nba", position: "C", image: "https://a.espncdn.com/i/headshots/nba/players/full/3059318.png", stats: { pts: 35.2, reb: 11.0, ast: 5.7, fg: 54.2, ts: 65.5 } },
];

const MOCK_TEAMS = [
    { id: "bos", name: "Boston Celtics", code: "BOS", league: "nba", logo: "https://a.espncdn.com/i/teamlogos/nba/500/bos.png", record: "32-9", stats: { ppg: 120.5, oppg: 108.2, pace: 101.2, ortg: 122.4, drtg: 110.1 } },
    { id: "den", name: "Denver Nuggets", code: "DEN", league: "nba", logo: "https://a.espncdn.com/i/teamlogos/nba/500/den.png", record: "30-12", stats: { ppg: 118.4, oppg: 112.1, pace: 99.8, ortg: 120.1, drtg: 113.4 } },
    { id: "okc", name: "Oklahoma City Thunder", code: "OKC", league: "nba", logo: "https://a.espncdn.com/i/teamlogos/nba/500/okc.png", record: "33-8", stats: { ppg: 119.2, oppg: 107.5, pace: 100.5, ortg: 121.2, drtg: 109.5 } },
    { id: "cle", name: "Cleveland Cavaliers", code: "CLE", league: "nba", logo: "https://a.espncdn.com/i/teamlogos/nba/500/cle.png", record: "31-10", stats: { ppg: 117.8, oppg: 106.9, pace: 98.2, ortg: 120.8, drtg: 109.8 } },
    { id: "mil", name: "Milwaukee Bucks", code: "MIL", league: "nba", logo: "https://a.espncdn.com/i/teamlogos/nba/500/mil.png", record: "26-16", stats: { ppg: 115.5, oppg: 112.4, pace: 102.1, ortg: 117.2, drtg: 113.8 } },
    { id: "lal", name: "Los Angeles Lakers", code: "LAL", league: "nba", logo: "https://a.espncdn.com/i/teamlogos/nba/500/lal.png", record: "21-22", stats: { ppg: 114.2, oppg: 113.8, pace: 100.8, ortg: 115.5, drtg: 114.2 } },
];

type CompareMode = "players" | "teams";
type ViewMode = "search" | "compare";

export default function ProfilePage() {
    const [viewMode, setViewMode] = useState<ViewMode>("search");
    const [compareMode, setCompareMode] = useState<CompareMode>("players");
    const [searchQuery, setSearchQuery] = useState("");
    const [activeTab, setActiveTab] = useState("profile");

    // Comparison selections
    const [selectedPlayer1, setSelectedPlayer1] = useState<typeof MOCK_PLAYERS[0] | null>(null);
    const [selectedPlayer2, setSelectedPlayer2] = useState<typeof MOCK_PLAYERS[0] | null>(null);
    const [selectedTeam1, setSelectedTeam1] = useState<typeof MOCK_TEAMS[0] | null>(null);
    const [selectedTeam2, setSelectedTeam2] = useState<typeof MOCK_TEAMS[0] | null>(null);

    // Filtered results
    const filteredPlayers = useMemo(() => {
        if (!searchQuery) return MOCK_PLAYERS;
        return MOCK_PLAYERS.filter(p =>
            p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            p.team.toLowerCase().includes(searchQuery.toLowerCase())
        );
    }, [searchQuery]);

    const filteredTeams = useMemo(() => {
        if (!searchQuery) return MOCK_TEAMS;
        return MOCK_TEAMS.filter(t =>
            t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            t.code.toLowerCase().includes(searchQuery.toLowerCase())
        );
    }, [searchQuery]);

    // Select player/team for comparison
    const selectForComparison = (item: any, type: "player" | "team") => {
        if (type === "player") {
            if (!selectedPlayer1) setSelectedPlayer1(item);
            else if (!selectedPlayer2) {
                setSelectedPlayer2(item);
                setViewMode("compare");
            }
        } else {
            if (!selectedTeam1) setSelectedTeam1(item);
            else if (!selectedTeam2) {
                setSelectedTeam2(item);
                setViewMode("compare");
            }
        }
    };

    const clearComparison = () => {
        setSelectedPlayer1(null);
        setSelectedPlayer2(null);
        setSelectedTeam1(null);
        setSelectedTeam2(null);
        setViewMode("search");
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
                                <div className="w-12 h-12 bg-gold/10 border border-gold/20 rounded-2xl flex items-center justify-center">
                                    <User className="w-6 h-6 text-gold" />
                                </div>
                                <div>
                                    <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tighter">
                                        Player <span className="text-gold italic">Profile</span>
                                    </h1>
                                    <p className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase tracking-widest mt-1">
                                        Search • Compare • Analyze
                                    </p>
                                </div>
                            </div>

                            {/* Mode Toggle */}
                            <div className="flex items-center gap-2 bg-dash-card border border-dash-border rounded-xl p-1">
                                <button
                                    onClick={() => { setCompareMode("players"); clearComparison(); }}
                                    className={cn(
                                        "flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase transition-all",
                                        compareMode === "players"
                                            ? "bg-gold text-dash-bg"
                                            : "text-dash-text-muted hover:text-white"
                                    )}
                                >
                                    <User className="w-3.5 h-3.5" />
                                    Players
                                </button>
                                <button
                                    onClick={() => { setCompareMode("teams"); clearComparison(); }}
                                    className={cn(
                                        "flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase transition-all",
                                        compareMode === "teams"
                                            ? "bg-cyan text-dash-bg"
                                            : "text-dash-text-muted hover:text-white"
                                    )}
                                >
                                    <Users className="w-3.5 h-3.5" />
                                    Teams
                                </button>
                            </div>
                        </div>

                        {/* Search Bar */}
                        <div className="mt-4 relative">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-dash-text-muted" />
                            <input
                                type="text"
                                placeholder={compareMode === "players" ? "Search players by name or team..." : "Search teams by name..."}
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-12 pr-4 py-3 bg-dash-card border border-dash-border rounded-xl text-white placeholder:text-dash-text-muted focus:border-gold/50 focus:outline-none transition-colors"
                            />
                            {searchQuery && (
                                <button
                                    onClick={() => setSearchQuery("")}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-dash-text-muted hover:text-white"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            )}
                        </div>

                        {/* Comparison Slots */}
                        {(selectedPlayer1 || selectedTeam1) && (
                            <div className="mt-4 flex items-center gap-4">
                                <div className="flex items-center gap-2 px-3 py-2 bg-gold/10 border border-gold/20 rounded-xl">
                                    <span className="text-[10px] font-bold text-gold uppercase">Comparing:</span>
                                    {compareMode === "players" ? (
                                        <>
                                            <span className="text-xs font-bold text-white">{selectedPlayer1?.name || "Select 1st"}</span>
                                            <ArrowLeftRight className="w-4 h-4 text-gold" />
                                            <span className="text-xs font-bold text-white">{selectedPlayer2?.name || "Select 2nd"}</span>
                                        </>
                                    ) : (
                                        <>
                                            <span className="text-xs font-bold text-white">{selectedTeam1?.name || "Select 1st"}</span>
                                            <ArrowLeftRight className="w-4 h-4 text-cyan" />
                                            <span className="text-xs font-bold text-white">{selectedTeam2?.name || "Select 2nd"}</span>
                                        </>
                                    )}
                                </div>
                                <button
                                    onClick={clearComparison}
                                    className="px-3 py-2 bg-dash-card border border-dash-border rounded-xl text-[10px] font-bold text-dash-text-muted uppercase hover:text-white transition-colors"
                                >
                                    Clear
                                </button>
                            </div>
                        )}
                    </div>
                </header>

                {/* Main Content */}
                <main className="p-4 md:p-6 lg:p-8 pb-24 lg:pb-8">
                    <div className="max-w-[1600px] mx-auto">
                        <AnimatePresence mode="wait">
                            {viewMode === "search" ? (
                                <motion.div
                                    key="search"
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                >
                                    {compareMode === "players" ? (
                                        /* Player Grid */
                                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                            {filteredPlayers.map((player) => (
                                                <motion.div
                                                    key={player.id}
                                                    initial={{ opacity: 0, scale: 0.95 }}
                                                    animate={{ opacity: 1, scale: 1 }}
                                                    className={cn(
                                                        "bg-dash-card border rounded-2xl p-4 cursor-pointer transition-all hover:border-gold/30",
                                                        (selectedPlayer1?.id === player.id || selectedPlayer2?.id === player.id)
                                                            ? "border-gold/50 bg-gold/5"
                                                            : "border-dash-border"
                                                    )}
                                                    onClick={() => selectForComparison(player, "player")}
                                                >
                                                    <div className="flex items-center gap-4">
                                                        <div className="w-16 h-16 rounded-xl overflow-hidden bg-dash-bg">
                                                            <img
                                                                src={player.image}
                                                                alt={player.name}
                                                                className="w-full h-full object-cover"
                                                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                                            />
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <h3 className="text-sm font-bold text-white truncate">{player.name}</h3>
                                                            <div className="flex items-center gap-2 mt-1">
                                                                <span className="text-[10px] font-bold text-gold uppercase">{player.team}</span>
                                                                <span className="text-[10px] text-dash-text-muted">•</span>
                                                                <span className="text-[10px] text-dash-text-muted uppercase">{player.position}</span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center justify-between mt-4 pt-4 border-t border-dash-border">
                                                        <div className="text-center">
                                                            <div className="text-lg font-black text-gold">{player.stats.pts}</div>
                                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase">PPG</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-lg font-black text-white">{player.stats.reb}</div>
                                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase">RPG</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-lg font-black text-white">{player.stats.ast}</div>
                                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase">APG</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-lg font-black text-cyan">{player.stats.ts}%</div>
                                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase">TS%</div>
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            ))}
                                        </div>
                                    ) : (
                                        /* Team Grid */
                                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                            {filteredTeams.map((team) => (
                                                <motion.div
                                                    key={team.id}
                                                    initial={{ opacity: 0, scale: 0.95 }}
                                                    animate={{ opacity: 1, scale: 1 }}
                                                    className={cn(
                                                        "bg-dash-card border rounded-2xl p-4 cursor-pointer transition-all hover:border-cyan/30",
                                                        (selectedTeam1?.id === team.id || selectedTeam2?.id === team.id)
                                                            ? "border-cyan/50 bg-cyan/5"
                                                            : "border-dash-border"
                                                    )}
                                                    onClick={() => selectForComparison(team, "team")}
                                                >
                                                    <div className="flex items-center gap-4">
                                                        <div className="w-16 h-16 rounded-xl overflow-hidden bg-dash-bg flex items-center justify-center p-2">
                                                            <img
                                                                src={team.logo}
                                                                alt={team.name}
                                                                className="w-full h-full object-contain"
                                                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                                            />
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <h3 className="text-sm font-bold text-white truncate">{team.name}</h3>
                                                            <div className="flex items-center gap-2 mt-1">
                                                                <span className="text-[10px] font-bold text-cyan uppercase">{team.code}</span>
                                                                <span className="text-[10px] text-dash-text-muted">•</span>
                                                                <span className="text-[10px] text-dash-text-muted">{team.record}</span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center justify-between mt-4 pt-4 border-t border-dash-border">
                                                        <div className="text-center">
                                                            <div className="text-lg font-black text-gold">{team.stats.ppg}</div>
                                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase">PPG</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-lg font-black text-white">{team.stats.oppg}</div>
                                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase">OPPG</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-lg font-black text-cyan">{team.stats.ortg}</div>
                                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase">ORtg</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-lg font-black text-white">{team.stats.drtg}</div>
                                                            <div className="text-[8px] font-bold text-dash-text-muted uppercase">DRtg</div>
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            ))}
                                        </div>
                                    )}
                                </motion.div>
                            ) : (
                                /* Comparison View */
                                <motion.div
                                    key="compare"
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                    className="space-y-6"
                                >
                                    {compareMode === "players" && selectedPlayer1 && selectedPlayer2 ? (
                                        <PlayerComparison player1={selectedPlayer1} player2={selectedPlayer2} />
                                    ) : compareMode === "teams" && selectedTeam1 && selectedTeam2 ? (
                                        <TeamComparison team1={selectedTeam1} team2={selectedTeam2} />
                                    ) : null}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </main>
            </div>

            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
    );
}

/* Player Comparison Component */
function PlayerComparison({ player1, player2 }: { player1: typeof MOCK_PLAYERS[0]; player2: typeof MOCK_PLAYERS[0] }) {
    const statCategories = [
        { key: "pts", label: "Points", color1: "gold", color2: "cyan" },
        { key: "reb", label: "Rebounds", color1: "gold", color2: "cyan" },
        { key: "ast", label: "Assists", color1: "gold", color2: "cyan" },
        { key: "fg", label: "FG%", color1: "gold", color2: "cyan" },
        { key: "ts", label: "TS%", color1: "gold", color2: "cyan" },
    ];

    return (
        <div className="bg-dash-card border border-dash-border rounded-3xl overflow-hidden">
            {/* Header with Player Photos */}
            <div className="flex items-center justify-between p-6 bg-dash-bg">
                <div className="flex items-center gap-4">
                    <div className="w-20 h-20 rounded-2xl overflow-hidden bg-gold/10 border-2 border-gold">
                        <img src={player1.image} alt={player1.name} className="w-full h-full object-cover" />
                    </div>
                    <div>
                        <h3 className="text-lg font-black text-white">{player1.name}</h3>
                        <div className="text-xs font-bold text-gold uppercase">{player1.team} • {player1.position}</div>
                    </div>
                </div>

                <div className="px-6 py-3 bg-dash-card rounded-xl border border-dash-border">
                    <span className="text-2xl font-black text-white">VS</span>
                </div>

                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <h3 className="text-lg font-black text-white">{player2.name}</h3>
                        <div className="text-xs font-bold text-cyan uppercase">{player2.team} • {player2.position}</div>
                    </div>
                    <div className="w-20 h-20 rounded-2xl overflow-hidden bg-cyan/10 border-2 border-cyan">
                        <img src={player2.image} alt={player2.name} className="w-full h-full object-cover" />
                    </div>
                </div>
            </div>

            {/* Stats Comparison */}
            <div className="p-6 space-y-4">
                {statCategories.map((stat) => {
                    const val1 = player1.stats[stat.key as keyof typeof player1.stats];
                    const val2 = player2.stats[stat.key as keyof typeof player2.stats];
                    const max = Math.max(val1, val2);
                    const pct1 = (val1 / max) * 100;
                    const pct2 = (val2 / max) * 100;
                    const winner = val1 > val2 ? 1 : val2 > val1 ? 2 : 0;

                    return (
                        <div key={stat.key} className="space-y-2">
                            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-dash-text-muted">
                                <span className={winner === 1 ? "text-gold" : ""}>{val1}</span>
                                <span>{stat.label}</span>
                                <span className={winner === 2 ? "text-cyan" : ""}>{val2}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 bg-dash-bg rounded-full overflow-hidden flex justify-end">
                                    <motion.div
                                        className="h-full bg-gold rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${pct1}%` }}
                                        transition={{ duration: 0.8 }}
                                    />
                                </div>
                                <div className="w-px h-4 bg-dash-border" />
                                <div className="flex-1 h-2 bg-dash-bg rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-cyan rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${pct2}%` }}
                                        transition={{ duration: 0.8 }}
                                    />
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* Team Comparison Component */
function TeamComparison({ team1, team2 }: { team1: typeof MOCK_TEAMS[0]; team2: typeof MOCK_TEAMS[0] }) {
    const statCategories = [
        { key: "ppg", label: "Points Per Game" },
        { key: "oppg", label: "Opponent PPG" },
        { key: "pace", label: "Pace" },
        { key: "ortg", label: "Offensive Rating" },
        { key: "drtg", label: "Defensive Rating" },
    ];

    return (
        <div className="bg-dash-card border border-dash-border rounded-3xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-6 bg-dash-bg">
                <div className="flex items-center gap-4">
                    <div className="w-20 h-20 rounded-2xl overflow-hidden bg-gold/10 border-2 border-gold p-2">
                        <img src={team1.logo} alt={team1.name} className="w-full h-full object-contain" />
                    </div>
                    <div>
                        <h3 className="text-lg font-black text-white">{team1.name}</h3>
                        <div className="text-xs font-bold text-gold uppercase">{team1.record}</div>
                    </div>
                </div>

                <div className="px-6 py-3 bg-dash-card rounded-xl border border-dash-border">
                    <span className="text-2xl font-black text-white">VS</span>
                </div>

                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <h3 className="text-lg font-black text-white">{team2.name}</h3>
                        <div className="text-xs font-bold text-cyan uppercase">{team2.record}</div>
                    </div>
                    <div className="w-20 h-20 rounded-2xl overflow-hidden bg-cyan/10 border-2 border-cyan p-2">
                        <img src={team2.logo} alt={team2.name} className="w-full h-full object-contain" />
                    </div>
                </div>
            </div>

            {/* Stats Comparison */}
            <div className="p-6 space-y-4">
                {statCategories.map((stat) => {
                    const val1 = team1.stats[stat.key as keyof typeof team1.stats];
                    const val2 = team2.stats[stat.key as keyof typeof team2.stats];
                    const max = Math.max(val1, val2);
                    const pct1 = (val1 / max) * 100;
                    const pct2 = (val2 / max) * 100;
                    const winner = val1 > val2 ? 1 : val2 > val1 ? 2 : 0;

                    return (
                        <div key={stat.key} className="space-y-2">
                            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-dash-text-muted">
                                <span className={winner === 1 ? "text-gold" : ""}>{val1}</span>
                                <span>{stat.label}</span>
                                <span className={winner === 2 ? "text-cyan" : ""}>{val2}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 bg-dash-bg rounded-full overflow-hidden flex justify-end">
                                    <motion.div
                                        className="h-full bg-gold rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${pct1}%` }}
                                        transition={{ duration: 0.8 }}
                                    />
                                </div>
                                <div className="w-px h-4 bg-dash-border" />
                                <div className="flex-1 h-2 bg-dash-bg rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-cyan rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${pct2}%` }}
                                        transition={{ duration: 0.8 }}
                                    />
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
