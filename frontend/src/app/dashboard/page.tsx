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
import { cn } from "@/lib/utils";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";
import { PredictionCard } from "@/components/dashboard/PredictionCard";
import { PropCard } from "@/components/dashboard/PropCard";
import { Prediction, PlayerProp } from "@/types";

/**
 * Dashboard Index - Dark Theme
 * 
 * Main dashboard landing page showing overview of all leagues
 */

const LEAGUES = [
    { id: "nba", name: "NBA", fullName: "National Basketball Association" },
    { id: "ncaa", name: "NCAA", fullName: "Division I Basketball" },
];

// Mock data for demo
const MOCK_PREDICTION: Prediction = {
    id: "mock-1",
    league: "nba",
    time: "7:30 PM",
    date: "TODAY",
    awayTeam: {
        name: "Lakers",
        code: "LAL",
        logo: "https://a.espncdn.com/i/teamlogos/nba/500/lal.png",
        record: "21-22",
        stats: { pointsPerGame: 114.2, reboundsPerGame: 42.1, assistsPerGame: 28.3, fieldGoalPct: 48.2, threePointPct: 35.8, freeThrowPct: 77.1, netRating: 59.8 }
    },
    homeTeam: {
        name: "Celtics",
        code: "BOS",
        logo: "https://a.espncdn.com/i/teamlogos/nba/500/bos.png",
        record: "32-9",
        stats: { pointsPerGame: 120.5, reboundsPerGame: 47.4, assistsPerGame: 26.1, fieldGoalPct: 49.1, threePointPct: 38.9, freeThrowPct: 80.5, netRating: 65.4 }
    },
    marketTotal: 234.5,
    modelTotal: 238.2,
    edge: 3.7,
    confidence: "strong",
    trace: ["Baseline Efficiency: BOS (121.2) vs LAL (112.5) @ 101.2 Pace."],
    factors: [{ label: "Elite Offense", value: 88, impact: 'positive' }],
    forecastData: [{ time: "Q1", awayVal: 28, homeVal: 32 }]
};

const MOCK_PROPS: PlayerProp[] = [
    {
        id: "p1",
        name: "LeBron James",
        team: "Lakers",
        teamCode: "LAL",
        position: "Forward",
        image: "https://a.espncdn.com/i/headshots/nba/players/full/1966.png",
        propType: "PTS",
        line: 24.5,
        projection: 28.2,
        edge: 3.7,
        edgePct: 15.1,
        usageBoost: true,
        recentTrend: [1, 1, -1, 1, 1]
    },
];

export default function DashboardIndex() {
    const [props, setProps] = useState<PlayerProp[]>([]);
    const [audit, setAudit] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Fetch for NBA only as requested for "Top Props"
            const leagues = ['nba'];
            let allProps: PlayerProp[] = [];
            let latestAudit = null;

            for (const leagueId of leagues) {
                try {
                    const res = await fetch(`/api/predictions?league=${leagueId}&mode=safe`);
                    const data = await res.json();

                    if (data.audit && !latestAudit) latestAudit = data.audit;

                    if (data.games) {
                        data.games.forEach((game: any) => {
                            if (game.props && game.props.length > 0) {
                                game.props.forEach((p: any) => {
                                    // Generate multi-category props with sportsbook-style lines
                                    const categories = [
                                        { type: 'PTS', key: 'pts', threshold: 10 },
                                        { type: 'REB', key: 'reb', threshold: 4 },
                                        { type: 'AST', key: 'ast', threshold: 3 },
                                        { type: 'STL', key: 'stl', threshold: 0.5 },
                                        { type: 'BLK', key: 'blk', threshold: 0.5 },
                                        { type: 'TOV', key: 'tov', threshold: 1.5 },
                                        { type: '3PM', key: 'threes', threshold: 1.5 },
                                    ];

                                    categories.forEach(cat => {
                                        const val = p[cat.key];
                                        if (val && val >= cat.threshold) {
                                            // Sportsbook-style half-point line
                                            let baseline: number;
                                            if (val < 1.5) {
                                                baseline = 0.5;
                                            } else if (val < 2.5) {
                                                baseline = 1.5;
                                            } else {
                                                baseline = Math.floor(val / 0.5) * 0.5 - 0.5;
                                                if (baseline < 0.5) baseline = 0.5;
                                            }

                                            const edge = val - baseline;
                                            const edgePct = (edge / baseline) * 100;

                                            if (edge > 0) {
                                                allProps.push({
                                                    id: `${p.id || p.name}-${cat.type}`,
                                                    name: p.name,
                                                    team: p.team_label === 'A' ? game.away : game.home,
                                                    teamCode: p.team_label === 'A' ? game.away : game.home,
                                                    position: p.position || "G/F",
                                                    image: leagueId === 'nba' ? `https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/${p.id}.png` : "",
                                                    propType: cat.type as any,
                                                    line: baseline,
                                                    projection: val,
                                                    edge: Number(edge.toFixed(1)),
                                                    edgePct: Number(edgePct.toFixed(1)),
                                                    usageBoost: p.trace?.some((t: string) => t.includes("Usage")),
                                                    recentTrend: [1, 1, 0, 1, 1]
                                                });
                                            }
                                        }
                                    });
                                });
                            }
                        });
                    }
                } catch (e) {
                    console.error(`Error fetching ${leagueId} props:`, e);
                }
            }

            // Sort by edge percentage to find the "Top" props
            allProps.sort((a, b) => b.edgePct - a.edgePct);

            setProps(allProps.length > 0 ? allProps : MOCK_PROPS);
            if (latestAudit) setAudit(latestAudit);
        } catch (err) {
            console.error("Fetch error:", err);
            setProps(MOCK_PROPS);
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
                                        blow<span className="text-gold italic">rout</span>
                                    </h1>
                                    <p className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase tracking-widest mt-1">
                                        Advanced Basketball Predictions
                                    </p>
                                </div>
                            </div>

                            <button
                                onClick={fetchData}
                                className="p-3 bg-dash-card border border-dash-border rounded-xl hover:border-gold/30 transition-colors"
                            >
                                <RefreshCw className={cn("w-4 h-4 text-dash-text-muted", loading && "animate-spin")} />
                            </button>
                        </div>

                        {/* League Tabs */}
                        <div className="flex items-center gap-2 mt-4 overflow-x-auto no-scrollbar pb-1">
                            {LEAGUES.map((league) => (
                                <Link
                                    key={league.id}
                                    href={`/dashboard/${league.id}`}
                                    className="px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all whitespace-nowrap bg-dash-card border border-dash-border text-dash-text-muted hover:text-white hover:border-gold/30"
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

                            {/* Sidebar / Quick Actions */}
                            <section className="lg:col-span-8 space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {LEAGUES.map((league) => (
                                        <Link
                                            key={league.id}
                                            href={`/dashboard/${league.id}`}
                                            className="group block bg-dash-card border border-dash-border rounded-3xl p-8 hover:border-gold/30 hover:scale-[1.02] transition-all"
                                        >
                                            <div className="w-16 h-16 bg-gold/10 rounded-2xl flex items-center justify-center mb-6">
                                                <Trophy className="w-8 h-8 text-gold" />
                                            </div>
                                            <h3 className="text-2xl font-black text-white uppercase tracking-tight mb-2">
                                                {league.name}
                                            </h3>
                                            <p className="text-sm text-dash-text-muted leading-relaxed mb-6">
                                                Access advanced predictions, efficiency metrics, and line logic for {league.fullName}.
                                            </p>
                                            <div className="flex items-center justify-between pt-6 border-t border-dash-border">
                                                <span className="text-xs font-bold text-gold uppercase tracking-widest">
                                                    Enter Dashboard
                                                </span>
                                                <ChevronRight className="w-5 h-5 text-dash-text-muted group-hover:text-gold transition-colors" />
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            </section>

                            {/* Sidebar */}
                            <aside className="lg:col-span-4 space-y-6">
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
                                    <h3 className="text-sm font-black text-white uppercase tracking-wider mb-4">League Predictions</h3>
                                    <div className="space-y-2">
                                        {LEAGUES.map((league) => (
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

            <BottomNav />
        </div>
    );
}
