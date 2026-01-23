"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Info,
    ChevronDown,
    Zap,
    BarChart3,
    TrendingUp,
    Activity,
    Users,
    ShieldAlert,
    Award,
    X,
    Clock,
    ArrowUpRight,
    ArrowDownRight
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PlayerProp {
    id?: string | number;
    name: string;
    team_label: string;
    league?: string;
    pts: number;
    reb: number;
    ast: number;
    trace: string[];
}

interface TeamStats {
    adj_off: number;
    adj_def: number;
    adj_t: number;
    four_factors: {
        efg: number;
        tov: number;
        orb: number;
        ftr: number;
    };
}

interface GameProps {
    game: {
        matchup: string;
        away: string;
        home: string;
        market_total: number;
        model_total: number;
        edge: number;
        decision: string;
        mode: string;
        trace: string[];
        props?: PlayerProp[];
        statsA?: TeamStats;
        statsH?: TeamStats;
        injuries?: any[];
    };
    leagueColor: string;
    leagueBg: string;
    leagueBorder: string;
    leagueName: string;
}

export function UniversalMatchupCard({ game, leagueColor, leagueBg, leagueBorder, leagueName }: GameProps) {
    const [showTrace, setShowTrace] = useState(false);
    const [selectedPlayer, setSelectedPlayer] = useState<PlayerProp | null>(null);

    // Logic to determine badge type
    const isModeA = Math.abs(game.edge) > 10;
    const isModeB = Math.abs(game.edge) > 6 && !isModeA;
    const isPositiveEdge = game.edge > 0;

    return (
        <>
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                    "card overflow-hidden transition-all duration-200",
                    showTrace ? "ring-2 ring-primary/20" : ""
                )}
            >
                {/* Main Card Content */}
                <div className="p-6">
                    {/* Header Row */}
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-4">
                            <div className={cn(
                                "h-8 px-4 flex items-center bg-navy text-white text-[10px] font-black uppercase tracking-widest rounded-sm",
                                leagueBg, leagueColor
                            )}>
                                {leagueName}
                            </div>
                            <div className="flex items-center gap-2 text-primary">
                                <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                                <span className="text-[10px] font-black uppercase tracking-widest">Live Analysis</span>
                            </div>
                        </div>

                        <div className="flex items-center gap-1">
                            {isModeA ? (
                                <div className="px-3 py-1 bg-success text-white text-[9px] font-black uppercase rounded-full">
                                    Top Lock
                                </div>
                            ) : isModeB ? (
                                <div className="px-3 py-1 bg-primary text-white text-[9px] font-black uppercase rounded-full">
                                    High Value
                                </div>
                            ) : null}
                        </div>
                    </div>

                    {/* Matchup Display - Euro Style */}
                    <div className="flex flex-col lg:flex-row items-center justify-between gap-12">
                        {/* Teams */}
                        <div className="flex items-center gap-12 flex-1">
                            <div className="flex-1 text-center">
                                <div className="text-3xl font-black text-navy uppercase tracking-tighter mb-1">
                                    {game.away}
                                </div>
                                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Away</div>
                            </div>

                            <div className="flex flex-col items-center">
                                <div className="text-[10px] font-black text-primary uppercase italic mb-1">VS</div>
                                <div className="w-[1px] h-12 bg-gray-100" />
                            </div>

                            <div className="flex-1 text-center">
                                <div className="text-3xl font-black text-navy uppercase tracking-tighter mb-1">
                                    {game.home}
                                </div>
                                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Home</div>
                            </div>
                        </div>

                        {/* Prediction Stats - Clean Vertical Columns */}
                        <div className="flex items-stretch bg-gray-50 rounded-2xl p-6 gap-10 border border-gray-100">
                            <div className="flex flex-col items-center justify-center">
                                <span className="text-[9px] font-black text-gray-400 uppercase tracking-tighter mb-2">Market</span>
                                <span className="text-xl font-black text-navy">{game.market_total}</span>
                            </div>

                            <div className="w-[1px] bg-gray-200" />

                            <div className="flex flex-col items-center justify-center">
                                <span className="text-[9px] font-black text-primary uppercase tracking-tighter mb-2">Advance Model</span>
                                <span className="text-3xl font-black text-primary leading-none">{game.model_total}</span>
                            </div>

                            <div className="w-[1px] bg-gray-200" />

                            <div className="flex flex-col items-center justify-center">
                                <span className="text-[9px] font-black text-gray-400 uppercase tracking-tighter mb-2">Edge</span>
                                <div className={cn(
                                    "text-xl font-black flex items-center gap-1",
                                    isPositiveEdge ? "text-success" : "text-danger"
                                )}>
                                    {isPositiveEdge ? `+${game.edge}` : game.edge}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Footer Row */}
                    <div className="mt-6 pt-4 border-t border-border flex items-center justify-between">
                        <button
                            onClick={() => setShowTrace(!showTrace)}
                            className="flex items-center gap-2 text-sm font-semibold text-text-muted hover:text-primary transition-colors"
                        >
                            <BarChart3 className="w-4 h-4" />
                            View Analysis
                            <ChevronDown className={cn(
                                "w-4 h-4 transition-transform duration-300",
                                showTrace ? "rotate-180" : ""
                            )} />
                        </button>

                        {game.props && game.props.length > 0 && (
                            <div className="flex items-center gap-3">
                                <span className="text-xs font-semibold text-text-muted">
                                    {game.props.length} Player Props
                                </span>
                                <div className="flex -space-x-2">
                                    {game.props.slice(0, 5).map((p: PlayerProp, idx: number) => (
                                        <button
                                            key={idx}
                                            onClick={() => setSelectedPlayer(p)}
                                            className={cn(
                                                "w-8 h-8 rounded-full border-2 border-white overflow-hidden flex items-center justify-center transition-all hover:scale-110 hover:z-10",
                                                p.team_label === 'A' ? "bg-primary/10" : "bg-navy/10"
                                            )}
                                        >
                                            {p.id && p.league === 'nba' ? (
                                                <img
                                                    src={`https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/${p.id}.png`}
                                                    alt={p.name}
                                                    className="w-full h-full object-cover"
                                                    onError={(e) => {
                                                        (e.target as HTMLImageElement).style.display = 'none';
                                                    }}
                                                />
                                            ) : (
                                                <span className={cn(
                                                    "text-xs font-bold",
                                                    p.team_label === 'A' ? "text-primary" : "text-navy"
                                                )}>
                                                    {p.name.charAt(0)}
                                                </span>
                                            )}
                                        </button>
                                    ))}
                                    {game.props.length > 5 && (
                                        <div className="w-8 h-8 rounded-full bg-bg-subtle border-2 border-white flex items-center justify-center text-xs font-bold text-text-muted">
                                            +{game.props.length - 5}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Expanded Analysis Panel */}
                <AnimatePresence>
                    {showTrace && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="border-t border-border bg-bg-subtle"
                        >
                            <div className="p-6 space-y-8">
                                {/* Metrics Comparison */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    {/* Model Trace */}
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 text-sm font-semibold text-text-dark">
                                            <BarChart3 className="w-4 h-4 text-primary" />
                                            Model Calculation
                                        </div>
                                        <div className="space-y-2">
                                            {(() => {
                                                let currentVal = 0;
                                                return game.trace.map((t: string, idx: number) => {
                                                    const parts = t.split(":");
                                                    const label = parts[0].trim();
                                                    const valStr = parts[1]?.trim() || "0";
                                                    const val = parseFloat(valStr.replace(/[^+0-9.-]/g, '')) || 0;

                                                    const isBase = idx === 0;
                                                    currentVal = isBase ? val : currentVal + val;

                                                    const isPositive = val > 0 && !isBase;
                                                    const isNegative = val < 0;

                                                    return (
                                                        <div key={idx} className="flex items-center justify-between py-2 px-3 rounded-lg bg-white">
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-sm font-medium text-text-dark">{label}</span>
                                                                {!isBase && (
                                                                    <span className={cn(
                                                                        "text-xs font-bold px-2 py-0.5 rounded",
                                                                        isPositive ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
                                                                    )}>
                                                                        {val > 0 ? `+${val}` : val}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <span className="text-sm font-bold text-text-dark font-mono">
                                                                {currentVal.toFixed(1)}
                                                            </span>
                                                        </div>
                                                    );
                                                });
                                            })()}
                                        </div>
                                    </div>

                                    {/* Four Factors Grid */}
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 text-sm font-semibold text-text-dark">
                                            <TrendingUp className="w-4 h-4 text-primary" />
                                            Four Factors
                                        </div>
                                        <div className="bg-white rounded-lg overflow-hidden">
                                            <table className="w-full text-sm">
                                                <thead>
                                                    <tr className="bg-bg-subtle">
                                                        <th className="px-4 py-2 text-left font-semibold text-text-muted">Team</th>
                                                        <th className="px-4 py-2 text-center font-semibold text-text-muted">eFG%</th>
                                                        <th className="px-4 py-2 text-center font-semibold text-text-muted">TO%</th>
                                                        <th className="px-4 py-2 text-center font-semibold text-text-muted">ORB%</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr className="border-t border-border">
                                                        <td className="px-4 py-3 font-bold text-text-dark">{game.away}</td>
                                                        <td className="px-4 py-3 text-center font-mono">{game.statsA?.four_factors?.efg?.toFixed(1) || '—'}%</td>
                                                        <td className="px-4 py-3 text-center font-mono">{game.statsA?.four_factors?.tov?.toFixed(1) || '—'}%</td>
                                                        <td className="px-4 py-3 text-center font-mono">{game.statsA?.four_factors?.orb?.toFixed(1) || '—'}%</td>
                                                    </tr>
                                                    <tr className="border-t border-border">
                                                        <td className="px-4 py-3 font-bold text-primary">{game.home}</td>
                                                        <td className="px-4 py-3 text-center font-mono text-primary">{game.statsH?.four_factors?.efg?.toFixed(1) || '—'}%</td>
                                                        <td className="px-4 py-3 text-center font-mono text-primary">{game.statsH?.four_factors?.tov?.toFixed(1) || '—'}%</td>
                                                        <td className="px-4 py-3 text-center font-mono text-primary">{game.statsH?.four_factors?.orb?.toFixed(1) || '—'}%</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>

                                        {/* Efficiency Comparison */}
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="bg-white p-4 rounded-lg">
                                                <div className="text-xs text-text-muted font-medium mb-1">AdjOE Mismatch</div>
                                                <div className="text-lg font-bold text-text-dark font-mono">
                                                    {(game.statsA?.adj_off || 0) > (game.statsH?.adj_off || 0)
                                                        ? `+${((game.statsA?.adj_off || 0) - (game.statsH?.adj_off || 0)).toFixed(1)}`
                                                        : '—'}
                                                </div>
                                            </div>
                                            <div className="bg-white p-4 rounded-lg">
                                                <div className="text-xs text-text-muted font-medium mb-1">AdjDE Differential</div>
                                                <div className="text-lg font-bold text-text-dark font-mono">
                                                    {((game.statsA?.adj_def || 0) - (game.statsH?.adj_def || 0)).toFixed(1)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Injuries Section */}
                                {game.injuries && game.injuries.length > 0 && (
                                    <div className="space-y-4 pt-6 border-t border-border">
                                        <div className="flex items-center gap-2 text-sm font-semibold text-danger">
                                            <ShieldAlert className="w-4 h-4" />
                                            Injury Report
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            {game.injuries.map((inj: any, idx: number) => (
                                                <div key={idx} className="flex gap-3 items-start p-4 rounded-lg bg-danger/5 border border-danger/10">
                                                    <Users className="w-5 h-5 text-danger shrink-0 mt-0.5" />
                                                    <div>
                                                        <div className="font-semibold text-text-dark">
                                                            {inj.name} <span className="text-danger">[{inj.status}]</span>
                                                        </div>
                                                        <p className="text-sm text-text-muted mt-1">{inj.note}</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Player Props Section */}
                                {game.props && game.props.length > 0 && (
                                    <div className="space-y-4 pt-6 border-t border-border">
                                        <div className="flex items-center gap-2 text-sm font-semibold text-text-dark">
                                            <Zap className="w-4 h-4 text-warning" />
                                            Player Projections
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                            {game.props.map((p: PlayerProp, idx: number) => (
                                                <button
                                                    key={idx}
                                                    onClick={() => setSelectedPlayer(p)}
                                                    className="bg-white p-4 rounded-lg border border-border hover:border-primary hover:shadow-md transition-all text-left group"
                                                >
                                                    <div className="flex items-center justify-between mb-3">
                                                        <div className="flex items-center gap-2">
                                                            <span className={cn(
                                                                "text-xs px-2 py-0.5 rounded font-semibold",
                                                                p.team_label === 'A' ? "bg-primary/10 text-primary" : "bg-navy/10 text-navy"
                                                            )}>
                                                                {p.team_label === 'A' ? 'AWAY' : 'HOME'}
                                                            </span>
                                                            <span className="font-semibold text-text-dark">{p.name}</span>
                                                        </div>
                                                        <Award className="w-4 h-4 text-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                                                    </div>
                                                    <div className="flex items-center gap-6 text-sm">
                                                        <div>
                                                            <span className="text-text-muted">PTS</span>
                                                            <span className="ml-2 font-bold text-primary">{p.pts}</span>
                                                        </div>
                                                        <div>
                                                            <span className="text-text-muted">REB</span>
                                                            <span className="ml-2 font-bold text-text-dark">{p.reb}</span>
                                                        </div>
                                                        <div>
                                                            <span className="text-text-muted">AST</span>
                                                            <span className="ml-2 font-bold text-text-dark">{p.ast}</span>
                                                        </div>
                                                    </div>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>

            {/* Player Intel Modal */}
            <AnimatePresence>
                {selectedPlayer && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden"
                        >
                            <button
                                onClick={() => setSelectedPlayer(null)}
                                className="absolute top-4 right-4 w-10 h-10 rounded-full bg-bg-subtle flex items-center justify-center text-text-muted hover:text-text-dark transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>

                            <div className="p-8">
                                {/* Player Header */}
                                <div className="flex items-center gap-4 mb-8">
                                    <div className={cn(
                                        "w-16 h-16 rounded-full overflow-hidden flex items-center justify-center text-2xl font-bold text-white",
                                        selectedPlayer.team_label === 'A'
                                            ? "bg-gradient-to-br from-primary to-primary-dark"
                                            : "bg-gradient-to-br from-navy to-navy-light"
                                    )}>
                                        {selectedPlayer.id && selectedPlayer.league === 'nba' ? (
                                            <img
                                                src={`https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/${selectedPlayer.id}.png`}
                                                alt={selectedPlayer.name}
                                                className="w-full h-full object-cover"
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).style.display = 'none';
                                                }}
                                            />
                                        ) : (
                                            selectedPlayer.name.charAt(0)
                                        )}
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={cn(
                                                "text-xs px-2 py-0.5 rounded font-semibold",
                                                selectedPlayer.team_label === 'A' ? "bg-primary/10 text-primary" : "bg-navy/10 text-navy"
                                            )}>
                                                {selectedPlayer.team_label === 'A' ? 'AWAY' : 'HOME'}
                                            </span>
                                        </div>
                                        <h2 className="text-2xl font-bold text-text-dark">{selectedPlayer.name}</h2>
                                    </div>
                                </div>

                                {/* Projection Stats */}
                                <div className="grid grid-cols-3 gap-4 mb-8">
                                    <div className="bg-bg-subtle p-6 rounded-xl text-center">
                                        <div className="text-xs text-text-muted font-medium mb-2">Points</div>
                                        <div className="text-3xl font-bold text-primary">{selectedPlayer.pts}</div>
                                    </div>
                                    <div className="bg-bg-subtle p-6 rounded-xl text-center">
                                        <div className="text-xs text-text-muted font-medium mb-2">Rebounds</div>
                                        <div className="text-3xl font-bold text-text-dark">{selectedPlayer.reb}</div>
                                    </div>
                                    <div className="bg-bg-subtle p-6 rounded-xl text-center">
                                        <div className="text-xs text-text-muted font-medium mb-2">Assists</div>
                                        <div className="text-3xl font-bold text-text-dark">{selectedPlayer.ast}</div>
                                    </div>
                                </div>

                                {/* Trace Details */}
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-sm font-semibold text-text-dark">Projection Breakdown</h3>
                                        <Activity className="w-4 h-4 text-text-muted" />
                                    </div>
                                    <div className="space-y-2">
                                        {selectedPlayer.trace.map((tr, idx) => (
                                            <div key={idx} className="flex items-center justify-between py-3 px-4 rounded-lg bg-bg-subtle">
                                                <span className="text-sm text-text-muted">{tr.split(":")[0]}</span>
                                                <span className="text-sm font-bold text-text-dark font-mono">{tr.split(":")[1] || ""}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </>
    );
}
