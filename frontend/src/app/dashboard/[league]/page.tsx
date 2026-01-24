"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
    Trophy,
    Target,
    TrendingUp,
    Calendar,
    RefreshCw,
    Zap,
    ChevronRight,
    BarChart3
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";
import { PredictionCard } from "@/components/dashboard/PredictionCard";
import { PropCard } from "@/components/dashboard/PropCard";
import { Prediction, PlayerProp } from "@/types";

/**
 * League Dashboard - Dark Theme
 * 
 * Displays predictions for a specific league (NBA, NCAA, EURO, etc.)
 * with consistent dark theme styling
 */

const LEAGUES = [
    { id: "nba", name: "NBA", fullName: "National Basketball Association" },
    { id: "ncaa", name: "NCAA", fullName: "Division I Basketball" },
    { id: "euro", name: "EURO", fullName: "EuroLeague & Eurocup" },
    { id: "nbl", name: "NBL", fullName: "Australia NBL" },
    { id: "acb", name: "ACB", fullName: "Liga ACB Spain" },
];

const GET_MOCK_DATA = (leagueId: string): { prediction: Prediction; props: PlayerProp[] } => {
    const isNBA = leagueId === "nba";
    const isNCAA = leagueId === "ncaa";
    const isEuro = leagueId === "euro";
    const isNBL = leagueId === "nbl";
    const isACB = leagueId === "acb";

    const prediction: Prediction = {
        id: `mock-${leagueId}`,
        league: leagueId as any,
        time: "LIVE",
        date: "TODAY",
        awayTeam: {
            name: isNBA ? "Lakers" : isNCAA ? "Duke" : isEuro ? "Real Madrid" : isNBL ? "Wildcats" : "Barcelona",
            code: isNBA ? "LAL" : isNCAA ? "DUKE" : isEuro ? "RMA" : isNBL ? "PER" : "BAR",
            logo: isNBA ? "https://a.espncdn.com/i/teamlogos/nba/500/lal.png" :
                isNCAA ? "https://a.espncdn.com/i/teamlogos/ncaa/500/duke.png" :
                    isEuro ? "https://a.espncdn.com/combine/i/teamlogos/euro/500/512.png" :
                        "https://a.espncdn.com/i/teamlogos/basketball/500/default.png",
            record: "21-22",
            stats: { pointsPerGame: 114.2, reboundsPerGame: 42.1, assistsPerGame: 28.3, fieldGoalPct: 48.2, threePointPct: 35.8, freeThrowPct: 77.1, netRating: 59.8 }
        },
        homeTeam: {
            name: isNBA ? "Celtics" : isNCAA ? "North Carolina" : isEuro ? "Anadolu Efes" : isNBL ? "Kings" : "Real Madrid",
            code: isNBA ? "BOS" : isNCAA ? "UNC" : isEuro ? "EFS" : isNBL ? "SYD" : "RMA",
            logo: isNBA ? "https://a.espncdn.com/i/teamlogos/nba/500/bos.png" :
                isNCAA ? "https://a.espncdn.com/i/teamlogos/ncaa/500/unc.png" :
                    isEuro ? "https://a.espncdn.com/combine/i/teamlogos/euro/500/512.png" :
                        "https://a.espncdn.com/i/teamlogos/basketball/500/default.png",
            record: "32-9",
            stats: { pointsPerGame: 120.5, reboundsPerGame: 47.4, assistsPerGame: 26.1, fieldGoalPct: 49.1, threePointPct: 38.9, freeThrowPct: 80.5, netRating: 65.4 }
        },
        marketTotal: isNBA ? 234.5 : 145.5,
        modelTotal: isNBA ? 238.2 : 148.7,
        edge: 3.7,
        confidence: "strong",
        trace: ["Power Efficiency Ranking applied.", "Historical pace adjustment match."],
        factors: [{ label: "Efficiency", value: 85, impact: 'positive' }],
        forecastData: [{ time: "Q1", awayVal: 28, homeVal: 32 }]
    };

    const props: PlayerProp[] = [
        {
            id: `p-${leagueId}`,
            name: isNBA ? "LeBron James" : isNCAA ? "RJ Davis" : "Facundo Campazzo",
            team: prediction.awayTeam.name,
            teamCode: prediction.awayTeam.code,
            position: "G/F",
            image: isNBA ? "https://a.espncdn.com/i/headshots/nba/players/full/1966.png" : "",
            propType: "PTS",
            line: 24.5,
            projection: 28.2,
            edge: 3.7,
            edgePct: 15.1,
            usageBoost: true,
            recentTrend: [1, 1, -1, 1, 1]
        }
    ];

    return { prediction, props };
};

export default function LeagueDashboard() {
    const params = useParams();
    const leagueId = (params.league as string) || "nba";
    const currentLeague = LEAGUES.find(l => l.id === leagueId) || LEAGUES[0];

    const [games, setGames] = useState<Prediction[]>([]);
    const [props, setProps] = useState<PlayerProp[]>([]);
    const [audit, setAudit] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [mode, setMode] = useState("safe");
    const [activeTab, setActiveTab] = useState("home");

    useEffect(() => {
        fetchData();
    }, [leagueId, mode]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/predictions?league=${leagueId}&mode=${mode}`);
            const data = await res.json();

            if (data.games && data.games.length > 0) {
                // Transform API data to match our types
                const transformedGames: Prediction[] = data.games.map((g: any, idx: number) => ({
                    id: `${leagueId}-${idx}`,
                    league: leagueId,
                    time: g.time || "TBD",
                    date: g.date || "TODAY",
                    awayTeam: {
                        name: g.away?.name || g.away_team || "Away",
                        code: g.away?.code || g.away_tri || "AWY",
                        logo: g.away?.logo || "",
                        record: g.away?.record || "",
                        stats: {
                            pointsPerGame: g.away?.stats?.ppg || 100,
                            reboundsPerGame: g.away?.stats?.rpg || 40,
                            assistsPerGame: g.away?.stats?.apg || 25,
                            fieldGoalPct: 45,
                            threePointPct: 35,
                            freeThrowPct: 75,
                            netRating: 50
                        }
                    },
                    homeTeam: {
                        name: g.home?.name || g.home_team || "Home",
                        code: g.home?.code || g.home_tri || "HME",
                        logo: g.home?.logo || "",
                        record: g.home?.record || "",
                        stats: {
                            pointsPerGame: g.home?.stats?.ppg || 100,
                            reboundsPerGame: g.home?.stats?.rpg || 40,
                            assistsPerGame: g.home?.stats?.apg || 25,
                            fieldGoalPct: 45,
                            threePointPct: 35,
                            freeThrowPct: 75,
                            netRating: 50
                        }
                    },
                    marketTotal: g.market_total || g.marketTotal || 220,
                    modelTotal: g.model_total || g.modelTotal || 225,
                    edge: g.edge || 2.5,
                    confidence: g.confidence || "lean",
                    trace: g.trace || [],
                    factors: g.factors || [],
                    forecastData: g.forecastData || []
                }));
                setGames(transformedGames);
            } else {
                // Use dynamic mock data if no API data
                const mock = GET_MOCK_DATA(leagueId);
                setGames([mock.prediction]);
                setProps(mock.props);
            }

            if (data.audit) setAudit(data.audit);
        } catch (err) {
            console.error("Fetch error:", err);
            const mock = GET_MOCK_DATA(leagueId);
            setGames([mock.prediction]);
            setProps(mock.props);
        } finally {
            setLoading(false);
        }
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
                                    <Trophy className="w-6 h-6 text-gold" />
                                </div>
                                <div>
                                    <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tighter">
                                        {currentLeague.name} <span className="text-gold italic">Dashboard</span>
                                    </h1>
                                    <div className="flex items-center gap-2 mt-1">
                                        <div className={cn(
                                            "w-1.5 h-1.5 rounded-full animate-pulse",
                                            games[0]?.id.startsWith('mock') ? "bg-dash-text-muted" : "bg-dash-success"
                                        )} />
                                        <p className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase tracking-widest">
                                            {games[0]?.id.startsWith('mock') ? "Demo Mode (No Live Data)" : "Live Database Connection"}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-3">
                                {/* Mode Toggle */}
                                <div className="flex items-center gap-2 bg-dash-card border border-dash-border rounded-xl p-1">
                                    <button
                                        onClick={() => setMode("safe")}
                                        className={cn(
                                            "px-4 py-2 rounded-lg text-xs font-bold uppercase transition-all",
                                            mode === "safe"
                                                ? "bg-gold text-dash-bg"
                                                : "text-dash-text-muted hover:text-white"
                                        )}
                                    >
                                        Safe
                                    </button>
                                    <button
                                        onClick={() => setMode("full")}
                                        className={cn(
                                            "px-4 py-2 rounded-lg text-xs font-bold uppercase transition-all",
                                            mode === "full"
                                                ? "bg-cyan text-dash-bg"
                                                : "text-dash-text-muted hover:text-white"
                                        )}
                                    >
                                        Full
                                    </button>
                                </div>

                                {/* Refresh */}
                                <button
                                    onClick={fetchData}
                                    className="p-3 bg-dash-card border border-dash-border rounded-xl hover:border-gold/30 transition-colors"
                                >
                                    <RefreshCw className={cn("w-4 h-4 text-dash-text-muted", loading && "animate-spin")} />
                                </button>
                            </div>
                        </div>

                        {/* League Tabs */}
                        <div className="flex items-center gap-2 mt-4 overflow-x-auto no-scrollbar pb-1">
                            {LEAGUES.map((league) => (
                                <Link
                                    key={league.id}
                                    href={`/dashboard/${league.id}`}
                                    className={cn(
                                        "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all whitespace-nowrap",
                                        league.id === leagueId
                                            ? "bg-gold text-dash-bg"
                                            : "bg-dash-card border border-dash-border text-dash-text-muted hover:text-white"
                                    )}
                                >
                                    {league.name}
                                </Link>
                            ))}
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="p-4 md:p-6 lg:p-8 pb-24 lg:pb-8">
                    <div className="max-w-[1600px] mx-auto">
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

                            {/* Games List */}
                            <section className="lg:col-span-8 space-y-6">
                                <div className="flex items-center justify-between">
                                    <h2 className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                                        <Target className="w-4 h-4 text-gold" />
                                        Model Predictions
                                    </h2>
                                    <span className="text-[10px] font-bold text-dash-text-muted">
                                        {games.length} active insights
                                    </span>
                                </div>

                                {loading ? (
                                    <div className="bg-dash-card border border-dash-border rounded-3xl p-12 flex flex-col items-center justify-center gap-4">
                                        <RefreshCw className="w-8 h-8 text-gold animate-spin" />
                                        <p className="text-sm font-bold text-dash-text-muted">Loading predictions...</p>
                                    </div>
                                ) : games.length > 0 ? (
                                    <div className="space-y-4">
                                        {games.map((game) => (
                                            <PredictionCard key={game.id} prediction={game} />
                                        ))}
                                    </div>
                                ) : (
                                    <div className="bg-dash-card border border-dash-border rounded-3xl p-12 flex flex-col items-center justify-center gap-4">
                                        <Calendar className="w-8 h-8 text-dash-text-muted" />
                                        <div className="text-center">
                                            <p className="text-sm font-bold text-white">No games available</p>
                                            <p className="text-xs text-dash-text-muted mt-1">Check back later for {currentLeague.name} predictions</p>
                                        </div>
                                    </div>
                                )}
                            </section>

                            {/* Sidebar */}
                            <aside className="lg:col-span-4 space-y-6">
                                {/* Performance Card */}
                                <div className="bg-dash-card border border-dash-border rounded-3xl p-6">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-sm font-black text-white uppercase tracking-wider">Model Performance</h3>
                                        <TrendingUp className="w-5 h-5 text-gold" />
                                    </div>

                                    <div className="space-y-4">
                                        <div>
                                            <div className="flex items-end justify-between mb-2">
                                                <span className="text-3xl font-black text-gold">
                                                    {audit?.last_48h?.pct ? `${audit.last_48h.pct}%` : "84.2%"}
                                                </span>
                                                <span className="text-xs font-bold text-dash-success">↑ 2.1%</span>
                                            </div>
                                            <p className="text-[10px] text-dash-text-muted uppercase">Win rate (48h)</p>
                                        </div>

                                        <div className="h-2 bg-dash-bg rounded-full overflow-hidden">
                                            <motion.div
                                                className="h-full bg-gold"
                                                initial={{ width: 0 }}
                                                animate={{ width: `${audit?.last_48h?.pct || 84.2}%` }}
                                                transition={{ duration: 1 }}
                                            />
                                        </div>

                                        <div className="text-xs text-dash-text-muted">
                                            Record: <span className="font-bold text-white">
                                                {audit?.last_48h?.wins || 24}W - {audit?.last_48h?.losses || 11}L
                                            </span>
                                        </div>
                                    </div>

                                    <Link
                                        href="/performance"
                                        className="mt-4 w-full block text-center py-3 rounded-xl border border-dash-border text-xs font-bold text-dash-text-muted uppercase tracking-widest hover:border-gold/30 hover:text-white transition-colors"
                                    >
                                        View Full History
                                    </Link>
                                </div>

                                {/* Props Card */}
                                <div className="bg-dash-card border border-dash-border rounded-3xl p-6">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                                            <Zap className="w-4 h-4 text-gold fill-current" />
                                            Top Props
                                        </h3>
                                        <Link href="/props" className="text-[9px] font-bold text-gold uppercase hover:underline">
                                            View All
                                        </Link>
                                    </div>

                                    <div className="space-y-3">
                                        {props.slice(0, 3).map((prop) => (
                                            <PropCard key={prop.id} prop={prop} />
                                        ))}
                                    </div>
                                </div>

                                {/* League Switcher */}
                                <div className="bg-dash-card border border-dash-border rounded-3xl p-6">
                                    <h3 className="text-sm font-black text-white uppercase tracking-wider mb-4">Other Leagues</h3>
                                    <div className="space-y-2">
                                        {LEAGUES.filter(l => l.id !== leagueId).slice(0, 3).map((league) => (
                                            <Link
                                                key={league.id}
                                                href={`/dashboard/${league.id}`}
                                                className="flex items-center justify-between p-3 rounded-xl bg-dash-bg hover:bg-dash-bg-secondary border border-transparent hover:border-dash-border transition-all group"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 bg-gold/10 rounded-lg flex items-center justify-center">
                                                        <Trophy className="w-4 h-4 text-gold" />
                                                    </div>
                                                    <div>
                                                        <div className="text-xs font-bold text-white uppercase">{league.name}</div>
                                                        <div className="text-[9px] text-dash-text-muted">{league.fullName}</div>
                                                    </div>
                                                </div>
                                                <ChevronRight className="w-4 h-4 text-dash-text-muted group-hover:text-gold transition-colors" />
                                            </Link>
                                        ))}
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </div>
                </main>
            </div>

            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
    );
}
