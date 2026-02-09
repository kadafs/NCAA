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
import { NCAA_LOGO_MAP } from "@/lib/ncaa-mappings";

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

/**
 * Normalized string helper: removes all non-alphanumeric, lowercases, and trims.
 */
const normalize = (str: string) => {
    return (str || "")
        .toLowerCase()
        .trim()
        .replace(/\./g, '')
        .replace(/\(/g, '')
        .replace(/\)/g, '')
        .replace(/'/g, '')
        .replace(/-/g, '')
        .replace(/&/g, 'and')
        .replace(/\s+/g, '');
};

/**
 * NBA Abbreviation Mapping: ESPN Scoreboard vs Prediction Engine
 */
const NBA_ABBR_MAP: Record<string, string> = {
    "gs": "gsw",
    "gsw": "gsw",
    "phx": "pho",
    "pho": "pho",
    "bkn": "bk",
    "bk": "bk",
    "no": "nop",
    "nop": "nop",
    "sa": "sas",
    "sas": "sas",
    "ny": "nyk",
    "nyk": "nyk"
};

/**
 * NCAA Name Aliases: Scoreboard vs Engine
 */
const NCAA_ALIASES: Record<string, string[]> = {
    "albany": ["ua albany", "u albany", "albany ny"],
    "penn state": ["penn st.", "penn st"],
    "umass lowell": ["umas low", "umas lowell"],
    "fairleigh dickinson": ["fairleigh dickinson", "fdu"],
    "saint mary's": ["st. mary's (ca)", "st marys ca", "st marys"],
    "st. thomas": ["st thomas mn", "st thomas"],
    "unc wilmington": ["uncw"],
    "unc greensboro": ["uncg"],
    "unc asheville": ["unca"],
    "grambling state": ["grambling"],
    "southeastern louisiana": ["southeastern la.", "southeastern la", "sela"],
    "stephen f austin": ["sfa"],
    "ut rio grande valley": ["utrgv", "texas rio grande valley"],
    "nicholls state": ["nicholls"],
    "arkansas pine bluff": ["ark.-pine bluff", "ark pine bluff", "uapb"],
    "saint francis": ["st. francis (pa)", "st francis pa"],
    "chicago state": ["chicago st", "chicago st."],
    "prairie view am": ["prairie view"],
    "incarnate word": ["uiw"],
    "mcneese state": ["mcneese"],
    "mid-atlantic christian": ["mid-atlantic christ"]
};

export default function ScoreboardPage() {
    const [selectedDate, setSelectedDate] = useState(getCurrentETDate());
    const [selectedLeague, setSelectedLeague] = useState("All");
    const [games, setGames] = useState<Game[]>([]);
    const [predictions, setPredictions] = useState<Record<string, any>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch games and predictions when date changes
    useEffect(() => {
        fetchData();
    }, [selectedDate]);

    const fetchData = async () => {
        setLoading(true);
        setError(null);

        try {
            const dateStr = formatDateForAPI(selectedDate);

            // Fetch scoreboard data and predictions in parallel
            const [ncaaData, nbaData, ncaaPreds, nbaPreds] = await Promise.allSettled([
                fetchScoreboard('basketball-men', 'd1', dateStr),
                fetchNBAScoreboard(selectedDate),
                fetch('/api/predictions?league=ncaa&mode=safe').then(r => r.json()),
                fetch('/api/predictions?league=nba&mode=safe').then(r => r.json())
            ]);

            // Build prediction lookup map
            const predMap: Record<string, any> = {};

            const processPreds = (data: any) => {
                if (data.status === 'fulfilled' && data.value.games) {
                    data.value.games.forEach((g: any) => {
                        const awayCodeRaw = (g.away_details?.code || g.away || "");
                        const homeCodeRaw = (g.home_details?.code || g.home || "");
                        const awayNameRaw = (g.away_details?.name || g.away || "");
                        const homeNameRaw = (g.home_details?.name || g.home || "");

                        const aCode = normalize(awayCodeRaw);
                        const hCode = normalize(homeCodeRaw);
                        const aName = normalize(awayNameRaw);
                        const hName = normalize(homeNameRaw);

                        // Index by normalized code combination
                        if (aCode && hCode) {
                            predMap[`${aCode}_vs_${hCode}`] = g;

                            // NBA Abbreviation Expansion (e.g. gsw vs pho -> gs vs phx)
                            const aAlias = NBA_ABBR_MAP[aCode];
                            const hAlias = NBA_ABBR_MAP[hCode];
                            if (aAlias || hAlias) {
                                const finalA = aAlias || aCode;
                                const finalH = hAlias || hCode;
                                predMap[`${finalA}_vs_${finalH}`] = g;
                            }
                        }

                        // Index by normalized name combination
                        if (aName && hName) {
                            predMap[`${aName}_vs_${hName}`] = g;

                            // NCAA Name Alias Expansion
                            Object.entries(NCAA_ALIASES).forEach(([engineName, scoreboardNames]) => {
                                const normEngine = normalize(engineName);
                                scoreboardNames.forEach(sName => {
                                    const normScore = normalize(sName);
                                    if (aName === normEngine) predMap[`${normScore}_vs_${hName}`] = g;
                                    if (hName === normEngine) predMap[`${aName}_vs_${normScore}`] = g;
                                    if (aName === normEngine && hName === normEngine) predMap[`${normScore}_vs_${normScore}`] = g; // unlikely but safe
                                });
                            });
                        }
                    });
                }
            };

            processPreds(ncaaPreds);
            processPreds(nbaPreds);
            setPredictions(predMap);

            const ncaaGames = ncaaData.status === 'fulfilled'
                ? transformNCAAGames(ncaaData.value.games || [], 'NCAA', predMap)
                : [];

            const nbaGames = nbaData.status === 'fulfilled'
                ? transformNCAAGames(nbaData.value.games || [], 'NBA', predMap)
                : [];

            setGames([...nbaGames, ...ncaaGames]);
        } catch (err) {
            console.error('Error fetching games:', err);
            setError('Failed to load games. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const transformNCAAGames = (ncaaGames: NCAAGame[], league: string = 'NCAA', predMap: Record<string, any>): Game[] => {
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

            // Match prediction from map
            const aCode = normalize(game.away.names.short);
            const hCode = normalize(game.home.names.short);
            const aFull = normalize(game.away.names.full);
            const hFull = normalize(game.home.names.full);

            // 1. Direct Code Match
            let match = predMap[`${aCode}_vs_${hCode}`];

            // 2. Direct Name Match
            if (!match) {
                match = predMap[`${aFull}_vs_${hFull}`];
            }

            // 3. Fuzzy/Substring Match (Lower confidence, but better than 150)
            if (!match) {
                const candidates = Object.keys(predMap);
                const fuzzyMatchKey = candidates.find(key => {
                    const [pAway, pHome] = key.split('_vs_');
                    // Check if scoreboard names contain prediction names or vice versa
                    return (aFull.includes(pAway) || pAway.includes(aFull)) &&
                        (hFull.includes(pHome) || pHome.includes(hFull));
                });
                if (fuzzyMatchKey) match = predMap[fuzzyMatchKey];
            }

            const total = match?.market_total || 150; // Fallback to 150 if truly not found
            const edge = match?.edge || 0;
            const side = match?.side || (edge > 0 ? 'OVER' : 'UNDER');
            const confidence = match?.confidence || "lean";

            return {
                id: game.gameID,
                league: league,
                status,
                time: timeDisplay,
                away: {
                    code: game.away.names.short,
                    name: game.away.names.full,
                    score: game.away.score,
                    logo: league === 'NBA'
                        ? `https://a.espncdn.com/i/teamlogos/nba/500/${game.away.names.short.toLowerCase()}.png`
                        : (() => {
                            const rawName = game.away.names.full || "";
                            const normName = normalize(rawName);
                            // Some logos need the "Slugified" version (dashes), some are in our special map
                            const slug = NCAA_LOGO_MAP[normName] || rawName.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                            return `/api/logo/${slug}`;
                        })()
                },
                home: {
                    code: game.home.names.short,
                    name: game.home.names.full,
                    score: game.home.score,
                    logo: league === 'NBA'
                        ? `https://a.espncdn.com/i/teamlogos/nba/500/${game.home.names.short.toLowerCase()}.png`
                        : (() => {
                            const rawName = game.home.names.full || "";
                            const normName = normalize(rawName);
                            const slug = NCAA_LOGO_MAP[normName] || rawName.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                            return `/api/logo/${slug}`;
                        })()
                },
                prediction: {
                    type: side as any,
                    line: total,
                    pick: `${side} ${total}`,
                    edge: Math.abs(edge),
                    confidence: (confidence.toLowerCase() as any) || "lean"
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
                                        onClick={fetchData}
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
    const [awayLogoError, setAwayLogoError] = useState(false);
    const [homeLogoError, setHomeLogoError] = useState(false);

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
                        <div className="w-8 h-8 bg-dash-bg-secondary rounded-lg flex items-center justify-center overflow-hidden">
                            {game.away.logo && !awayLogoError ? (
                                <img
                                    src={game.away.logo}
                                    alt={game.away.code}
                                    className="w-6 h-6 object-contain"
                                    onError={() => setAwayLogoError(true)}
                                />
                            ) : (
                                <span className="text-[10px] font-black text-white">{game.away.code[0]}</span>
                            )}
                        </div>
                        <span className="text-sm font-black text-white">{game.away.code}</span>
                    </div>
                    <span className="text-lg font-black text-white">
                        {game.away.score ?? '-'}
                    </span>
                </div>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-dash-bg-secondary rounded-lg flex items-center justify-center overflow-hidden">
                            {game.home.logo && !homeLogoError ? (
                                <img
                                    src={game.home.logo}
                                    alt={game.home.code}
                                    className="w-6 h-6 object-contain"
                                    onError={() => setHomeLogoError(true)}
                                />
                            ) : (
                                <span className="text-[10px] font-black text-white">{game.home.code[0]}</span>
                            )}
                        </div>
                        <span className="text-sm font-black text-white">{game.home.code}</span>
                    </div>
                    <span className="text-lg font-black text-white">
                        {game.home.score ?? '-'}
                    </span>
                </div>
            </div>

            {/* Prediction Footer */}
            <div className="px-3 sm:px-4 py-2 sm:py-3 bg-dash-bg-secondary border-t border-dash-border flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 flex-1">
                    <ConfidenceBadge confidence={game.prediction.confidence} />
                    <span className="text-[10px] sm:text-xs font-bold text-white truncate">{game.prediction.pick}</span>
                </div>
                <div className={cn(
                    "text-[9px] sm:text-[10px] font-black px-1.5 sm:px-2 py-0.5 sm:py-1 rounded flex-shrink-0",
                    game.prediction.edge > 4 ? "bg-gold/10 text-gold" : "bg-cyan/10 text-cyan"
                )}>
                    +{game.prediction.edge.toFixed(1)}
                </div>
            </div>
        </motion.div>
    );
}
