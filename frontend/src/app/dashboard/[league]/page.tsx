"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
    Trophy,
    Activity,
    Target,
    Zap,
    BarChart3,
    TrendingUp,
    Calendar,
    Clock,
    ChevronRight,
    Filter,
    RefreshCw
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { UniversalMatchupCard } from "@/components/UniversalMatchupCard";

const PLATFORM_STATS = [
    { label: "Active Games", value: "32", icon: Calendar, color: "text-primary" },
    { label: "Model Accuracy", value: "84.2%", icon: Target, color: "text-success" },
    { label: "Avg Edge", value: "+2.8", icon: TrendingUp, color: "text-primary" },
];

const LEAGUES = [
    { id: "nba", name: "NBA", fullName: "National Basketball Association", color: "text-red-600", bg: "bg-red-50", border: "border-red-200" },
    { id: "ncaa", name: "NCAA", fullName: "Division I Basketball", color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-200" },
    { id: "euro", name: "EURO", fullName: "European Leagues", color: "text-orange-600", bg: "bg-orange-50", border: "border-orange-200" },
];

export default function LeagueDashboard() {
    const params = useParams();
    const leagueId = params.league as string;
    const currentLeague = LEAGUES.find(l => l.id === leagueId) || LEAGUES[0];

    const [games, setGames] = useState<any[]>([]);
    const [audit, setAudit] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [mode, setMode] = useState("safe");

    useEffect(() => {
        fetchData();
    }, [leagueId, mode]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/predictions?league=${leagueId}&mode=${mode}`);
            const data = await res.json();
            if (data.games) setGames(data.games);
            if (data.audit) setAudit(data.audit);
        } catch (err) {
            console.error("Fetch error:", err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-bg-light">
            {/* Page Header */}
            <div className="bg-white border-b border-border">
                <div className="max-w-7xl mx-auto px-4 py-6">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <div className={cn("p-2 rounded-lg", currentLeague.bg)}>
                                    <Trophy className={cn("w-5 h-5", currentLeague.color)} />
                                </div>
                                <h1 className="text-2xl md:text-3xl font-bold text-text-dark text-display">
                                    {currentLeague.name} Predictions
                                </h1>
                            </div>
                            <p className="text-text-muted text-sm">
                                {currentLeague.fullName} • Updated in real-time
                            </p>
                        </div>

                        <div className="flex items-center gap-4">
                            {/* Mode Selector */}
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                                    Mode:
                                </span>
                                <div className="flex bg-bg-subtle rounded-lg p-1">
                                    <button
                                        onClick={() => setMode("safe")}
                                        className={cn(
                                            "px-4 py-1.5 rounded-md text-sm font-semibold transition-all",
                                            mode === "safe"
                                                ? "bg-white text-text-dark shadow-sm"
                                                : "text-text-muted hover:text-text-dark"
                                        )}
                                    >
                                        Safe
                                    </button>
                                    <button
                                        onClick={() => setMode("full")}
                                        className={cn(
                                            "px-4 py-1.5 rounded-md text-sm font-semibold transition-all",
                                            mode === "full"
                                                ? "bg-primary text-white shadow-sm"
                                                : "text-text-muted hover:text-text-dark"
                                        )}
                                    >
                                        Full
                                    </button>
                                </div>
                            </div>

                            {/* Refresh Button */}
                            <button
                                onClick={fetchData}
                                className="p-2 rounded-lg bg-bg-subtle hover:bg-border transition-colors"
                            >
                                <RefreshCw className={cn("w-5 h-5 text-text-muted", loading && "animate-spin")} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Stats Bar */}
            <div className="bg-white border-b border-border">
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="grid grid-cols-3 gap-4">
                        {PLATFORM_STATS.map((stat) => (
                            <div key={stat.label} className="flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-bg-subtle">
                                    <stat.icon className={cn("w-4 h-4", stat.color)} />
                                </div>
                                <div>
                                    <div className="text-xs text-text-muted font-medium">{stat.label}</div>
                                    <div className="text-lg font-bold text-text-dark">
                                        {stat.label === "Active Games" ? (games.length > 0 ? games.length : stat.value) : stat.value}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-4 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Games List */}
                    <section className="lg:col-span-8 space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-bold text-text-dark flex items-center gap-2">
                                <BarChart3 className={cn("w-5 h-5", currentLeague.color)} />
                                Today's Games
                            </h2>
                            <span className="text-sm text-text-muted">
                                {games.length} predictions available
                            </span>
                        </div>

                        <div className="space-y-4">
                            {games.length > 0 ? games.map((game, i) => (
                                <UniversalMatchupCard
                                    key={i}
                                    game={game}
                                    leagueColor={currentLeague.color}
                                    leagueBg={currentLeague.bg}
                                    leagueBorder={currentLeague.border}
                                    leagueName={currentLeague.name}
                                />
                            )) : (
                                <div className="card p-12 text-center">
                                    {loading ? (
                                        <div className="flex flex-col items-center gap-4">
                                            <RefreshCw className="w-8 h-8 text-primary animate-spin" />
                                            <p className="text-text-muted font-medium">
                                                Loading predictions...
                                            </p>
                                        </div>
                                    ) : (
                                        <div className="flex flex-col items-center gap-4">
                                            <div className="p-4 rounded-full bg-bg-subtle">
                                                <Calendar className="w-8 h-8 text-text-muted" />
                                            </div>
                                            <div>
                                                <p className="text-text-dark font-semibold mb-1">
                                                    No games available
                                                </p>
                                                <p className="text-text-muted text-sm">
                                                    Check back later for {currentLeague.name} predictions
                                                </p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </section>

                    {/* Sidebar */}
                    <aside className="lg:col-span-4 space-y-6">
                        {/* Performance Card */}
                        <div className="card p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-text-dark">Model Performance</h3>
                                <TrendingUp className="w-5 h-5 text-primary" />
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <div className="flex items-end justify-between mb-2">
                                        <span className="text-3xl font-bold text-text-dark">
                                            {audit?.last_48h?.pct ? `${audit.last_48h.pct}%` : "84.2%"}
                                        </span>
                                        <span className="text-sm font-semibold text-success">↑ 2.1%</span>
                                    </div>
                                    <p className="text-xs text-text-muted">
                                        Win rate over last 48 hours
                                    </p>
                                </div>

                                <div className="h-2 bg-bg-subtle rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-primary transition-all duration-1000 rounded-full"
                                        style={{ width: `${audit?.last_48h?.pct || 84.2}%` }}
                                    />
                                </div>

                                <div className="text-xs text-text-muted">
                                    Record: <span className="font-semibold text-text-dark">
                                        {audit?.last_48h?.wins || 24}W - {audit?.last_48h?.losses || 11}L
                                    </span>
                                </div>
                            </div>

                            <Link
                                href="/history"
                                className="mt-4 w-full block text-center py-2.5 rounded-lg border border-border text-sm font-semibold text-text-dark hover:bg-bg-subtle transition-colors"
                            >
                                View Full History
                            </Link>
                        </div>

                        {/* Player Props Card */}
                        <div className="card p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-text-dark">Top Player Props</h3>
                                <Zap className="w-5 h-5 text-warning" />
                            </div>

                            <div className="space-y-3">
                                {games.length > 0 ? (
                                    games.flatMap(g => g.props || []).slice(0, 5).map((p: any, idx: number) => (
                                        <div key={idx} className="flex items-center gap-3 p-3 rounded-lg bg-bg-subtle">
                                            <div className={cn(
                                                "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold",
                                                p.team_label === 'A' ? "bg-primary/10 text-primary" : "bg-navy/10 text-navy"
                                            )}>
                                                {p.id && leagueId === 'nba' ? (
                                                    <img
                                                        src={`https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/${p.id}.png`}
                                                        alt={p.name}
                                                        className="w-full h-full object-cover rounded-full"
                                                        onError={(e) => {
                                                            (e.target as HTMLImageElement).style.display = 'none';
                                                        }}
                                                    />
                                                ) : p.name.charAt(0)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-sm font-semibold text-text-dark truncate">
                                                    {p.name}
                                                </div>
                                                <div className="flex items-center gap-3 text-xs text-text-muted">
                                                    <span>PTS: <span className="font-semibold text-primary">{p.pts}</span></span>
                                                    <span>REB: {p.reb}</span>
                                                    <span>AST: {p.ast}</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-center py-4 text-sm text-text-muted">
                                        No prop data available
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* League Switcher */}
                        <div className="card p-6">
                            <h3 className="font-semibold text-text-dark mb-4">Other Leagues</h3>
                            <div className="space-y-2">
                                {LEAGUES.filter(l => l.id !== leagueId).map((league) => (
                                    <Link
                                        key={league.id}
                                        href={`/dashboard/${league.id}`}
                                        className="flex items-center justify-between p-3 rounded-lg hover:bg-bg-subtle transition-colors group"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={cn("p-2 rounded-lg", league.bg)}>
                                                <Trophy className={cn("w-4 h-4", league.color)} />
                                            </div>
                                            <div>
                                                <div className="font-semibold text-text-dark">{league.name}</div>
                                                <div className="text-xs text-text-muted">{league.fullName}</div>
                                            </div>
                                        </div>
                                        <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-primary transition-colors" />
                                    </Link>
                                ))}
                            </div>
                        </div>
                    </aside>
                </div>
            </div>
        </div>
    );
}
