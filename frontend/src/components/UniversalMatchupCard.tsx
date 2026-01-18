"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Info, ChevronDown, Zap, BarChart3, TrendingUp, Activity, Users, ShieldAlert, Award, X } from "lucide-react";
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

    return (
        <>
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                    "glass group p-0 rounded-[32px] border border-white/[0.04] overflow-hidden transition-all duration-500 hover:bg-white/[0.04]",
                    showTrace ? "ring-1 ring-accent-blue/20" : ""
                )}
            >
                <div className="p-8">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-3">
                            <div className={cn("px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider border", leagueBg, leagueColor, leagueBorder)}>
                                {leagueName}
                            </div>
                            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-green-500/5 border border-green-500/10">
                                <div className="w-1 h-1 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] animate-pulse" />
                                <span className="text-[8px] font-black text-green-400 uppercase tracking-tighter">Live Odds</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            {isModeA && (
                                <div className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-black uppercase tracking-[0.1em] shadow-[0_0_15px_rgba(16,185,129,0.1)]">
                                    LOCK: MODE A
                                </div>
                            )}
                            {isModeB && (
                                <div className="px-3 py-1 rounded-full bg-accent-blue/10 text-accent-blue border border-accent-blue/20 text-[9px] font-black uppercase tracking-[0.1em]">
                                    VALUE: MODE B
                                </div>
                            )}
                            <div className={cn(
                                "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest transition-colors",
                                game.decision === "PLAY" ? "bg-white/10 text-white" : "bg-white/5 text-gray-500 border border-white/5"
                            )}>
                                {game.decision}
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-col md:flex-row justify-between items-center gap-10">
                        <div className="flex-1 flex items-center gap-8 w-full md:w-auto">
                            <div className="space-y-1">
                                <div className="text-3xl font-black tracking-tighter text-display text-white">{game.away}</div>
                                <div className="text-sm text-gray-400 font-medium">at {game.home}</div>
                            </div>
                        </div>

                        <div className="flex items-center gap-12 w-full md:w-auto justify-between md:justify-end">
                            <div className="space-y-1.5 text-center md:text-right">
                                <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest leading-none text-nowrap">Market</div>
                                <div className="text-xl font-mono font-medium text-gray-400">{game.market_total}</div>
                            </div>
                            <div className="space-y-1.5 text-center md:text-right">
                                <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest leading-none text-nowrap">Model</div>
                                <div className="text-2xl font-mono font-black text-accent-blue">{game.model_total}</div>
                            </div>
                            <div className="space-y-1.5 text-center md:text-right min-w-[60px]">
                                <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest leading-none text-nowrap">Edge</div>
                                <div className={cn("text-xl font-mono font-black py-1 px-3 rounded-lg", game.edge > 0 ? "text-green-400 bg-green-400/5 shadow-[0_0_20px_rgba(74,222,128,0.05)]" : "text-red-400 bg-red-400/5")}>
                                    {game.edge > 0 ? `+${game.edge}` : game.edge}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="mt-10 flex items-center justify-between">
                        <button
                            onClick={() => setShowTrace(!showTrace)}
                            className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-gray-500 hover:text-white transition-colors group/btn"
                        >
                            <Zap className="w-3.5 h-3.5 opacity-50 text-accent-blue group-hover/btn:opacity-100 transition-opacity" />
                            Logic Intelligence
                            <ChevronDown className={cn("w-3.5 h-3.5 transition-transform duration-300", showTrace ? "rotate-180" : "")} />
                        </button>

                        {game.props && game.props.length > 0 && (
                            <div className="flex items-center gap-4">
                                <span className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">Player Intel</span>
                                <div className="flex -space-x-2">
                                    {/* Show up to 8 avatars */}
                                    {game.props.slice(0, 8).map((p: PlayerProp, idx: number) => (
                                        <button
                                            key={idx}
                                            onClick={() => setSelectedPlayer(p)}
                                            className={cn(
                                                "w-9 h-9 rounded-full border-2 border-[#0b0c10] overflow-hidden flex items-center justify-center transition-all hover:scale-110 hover:z-10 ring-1 ring-white/5 shadow-2xl relative group/avatar",
                                                p.team_label === 'A' ? "bg-accent-blue/10" : "bg-accent-orange/10"
                                            )}
                                        >
                                            {p.id && p.league === 'nba' ? (
                                                <img
                                                    src={`https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/${p.id}.png`}
                                                    alt={p.name}
                                                    className="w-full h-full object-cover scale-110 group-hover/avatar:scale-125 transition-transform"
                                                    onError={(e) => {
                                                        (e.target as HTMLImageElement).style.display = 'none';
                                                        (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
                                                    }}
                                                />
                                            ) : null}
                                            <span className={cn(
                                                "text-[11px] font-black pointer-events-none",
                                                p.id && p.league === 'nba' ? "hidden" : "",
                                                p.team_label === 'A' ? "text-accent-blue" : "text-accent-orange"
                                            )}>
                                                {p.name.charAt(0)}
                                            </span>
                                        </button>
                                    ))}
                                    {game.props.length > 8 && (
                                        <div className="w-8 h-8 rounded-full bg-white/5 border-2 border-[#0b0c10] flex items-center justify-center text-[10px] font-black text-gray-500 ring-1 ring-white/5">
                                            +{game.props.length - 8}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <AnimatePresence>
                    {showTrace && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                            className="border-t border-white/[0.04] bg-white/[0.01]"
                        >
                            <div className="p-8 space-y-12">
                                {/* Advanced Metrics Comparison */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                                    <div className="space-y-6">
                                        <div className="text-[10px] font-bold uppercase text-accent-blue tracking-widest opacity-80 flex items-center gap-2">
                                            <BarChart3 className="w-3.5 h-3.5" />
                                            Mathematical Footprint
                                        </div>
                                        <div className="space-y-3">
                                            {(() => {
                                                let currentVal = 0;
                                                return game.trace.map((t: string, idx: number) => {
                                                    const parts = t.split(":");
                                                    const label = parts[0].trim();
                                                    const valStr = parts[1]?.trim() || "0";
                                                    const val = parseFloat(valStr.replace(/[^+0-9.-]/g, '')) || 0;

                                                    const isBase = idx === 0;
                                                    const prevVal = currentVal;
                                                    currentVal = isBase ? val : currentVal + val;

                                                    const isPositive = val > 0 && !isBase;
                                                    const isNegative = val < 0;

                                                    return (
                                                        <div key={idx} className="group/trace relative">
                                                            <div className="flex items-center justify-between mb-1.5">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-[10px] text-gray-500 font-bold uppercase tracking-tight">{label}</span>
                                                                    {!isBase && (
                                                                        <span className={cn("text-[8px] font-black px-1.5 py-0.5 rounded", isPositive ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400")}>
                                                                            {val > 0 ? `+${val}` : val}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                <span className="text-[10px] font-mono font-bold text-white">
                                                                    {currentVal.toFixed(1)}
                                                                </span>
                                                            </div>
                                                            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden flex">
                                                                <motion.div
                                                                    initial={{ width: 0 }}
                                                                    animate={{ width: `${(currentVal / 300) * 100}%` }}
                                                                    transition={{ delay: idx * 0.1, duration: 0.5 }}
                                                                    className={cn("h-full", isBase ? "bg-white/20" : isPositive ? "bg-green-500/40" : isNegative ? "bg-red-500/40" : "bg-white/10")}
                                                                />
                                                            </div>
                                                        </div>
                                                    );
                                                });
                                            })()}
                                        </div>
                                    </div>

                                    <div className="space-y-6">
                                        <div className="text-[10px] font-bold uppercase text-sky-400 tracking-widest opacity-80 flex items-center gap-2">
                                            <TrendingUp className="w-3.5 h-3.5" />
                                            Advanced Metrics Grid
                                        </div>
                                        <div className="grid grid-cols-4 gap-4 p-5 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
                                            <div className="col-span-1" />
                                            <div className="text-[8px] font-black text-gray-500 uppercase text-center">eFG%</div>
                                            <div className="text-[8px] font-black text-gray-500 uppercase text-center">TO%</div>
                                            <div className="text-[8px] font-black text-gray-500 uppercase text-center">ORB%</div>

                                            <div className="text-[8px] font-black text-white uppercase">{game.away}</div>
                                            <div className="text-xs font-mono font-bold text-center text-gray-300">{game.statsA?.four_factors?.efg?.toFixed(1) || '—'}%</div>
                                            <div className="text-xs font-mono font-bold text-center text-gray-300">{game.statsA?.four_factors?.tov?.toFixed(1) || '—'}%</div>
                                            <div className="text-xs font-mono font-bold text-center text-gray-300">{game.statsA?.four_factors?.orb?.toFixed(1) || '—'}%</div>

                                            <div className="text-[8px] font-black text-accent-blue uppercase">{game.home}</div>
                                            <div className="text-xs font-mono font-bold text-center text-accent-blue">{game.statsH?.four_factors?.efg?.toFixed(1) || '—'}%</div>
                                            <div className="text-xs font-mono font-bold text-center text-accent-blue">{game.statsH?.four_factors?.tov?.toFixed(1) || '—'}%</div>
                                            <div className="text-xs font-mono font-bold text-center text-accent-blue">{game.statsH?.four_factors?.orb?.toFixed(1) || '—'}%</div>
                                        </div>

                                        <div className="flex gap-4">
                                            <div className="flex-1 p-4 rounded-xl bg-white/[0.01] border border-white/[0.04] space-y-2">
                                                <div className="text-[8px] font-black text-gray-600 uppercase">AdjOE Mismatch</div>
                                                <div className="text-sm font-mono font-black text-white">
                                                    {(game.statsA?.adj_off || 0) > (game.statsH?.adj_off || 0) ? `+${((game.statsA?.adj_off || 0) - (game.statsH?.adj_off || 0)).toFixed(1)}` : '—'}
                                                </div>
                                            </div>
                                            <div className="flex-1 p-4 rounded-xl bg-white/[0.01] border border-white/[0.04] space-y-2">
                                                <div className="text-[8px] font-black text-gray-600 uppercase">AdjDE Differential</div>
                                                <div className="text-sm font-mono font-black text-white">
                                                    {((game.statsA?.adj_def || 0) - (game.statsH?.adj_def || 0)).toFixed(1)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {game.injuries && game.injuries.length > 0 && (
                                    <div className="space-y-6 pt-8 border-t border-white/[0.04]">
                                        <div className="text-[10px] font-bold uppercase text-red-400 tracking-widest opacity-80 flex items-center gap-2">
                                            <ShieldAlert className="w-3.5 h-3.5" />
                                            Situational Intelligence
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {game.injuries.map((inj: any, idx: number) => (
                                                <div key={idx} className="flex gap-4 items-start p-4 rounded-2xl bg-red-500/[0.02] border border-red-500/10">
                                                    <div className="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
                                                        <Users className="w-4 h-4 text-red-400" />
                                                    </div>
                                                    <div className="space-y-1">
                                                        <div className="text-[10px] font-black text-white tracking-widest uppercase">{inj.name} <span className="text-red-400 ml-2">[{inj.status}]</span></div>
                                                        <p className="text-[10px] text-gray-500 leading-relaxed font-medium italic">"{inj.note}"</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {game.props && game.props.length > 0 && (
                                    <div className="space-y-6 pt-8 border-t border-white/[0.04]">
                                        <div className="text-[10px] font-bold uppercase text-sky-400 tracking-widest opacity-80 flex items-center gap-2">
                                            <TrendingUp className="w-3.5 h-3.5" />
                                            Direct Projections
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                            {game.props.map((p: PlayerProp, idx: number) => (
                                                <button
                                                    key={idx}
                                                    onClick={() => setSelectedPlayer(p)}
                                                    className="group/pcard relative p-4 rounded-2xl border transition-all duration-300 bg-white/[0.01] border-white/[0.04] hover:bg-white/[0.04] hover:border-accent-blue/30 text-left"
                                                >
                                                    <div className="flex items-center justify-between mb-3">
                                                        <div className="flex items-center gap-3">
                                                            <span className={cn("text-[8px] px-2 py-0.5 rounded-md font-black uppercase tracking-tighter", p.team_label === 'A' ? "bg-accent-blue/10 text-accent-blue" : "bg-accent-orange/10 text-accent-orange")}>
                                                                {p.team_label === 'A' ? 'AWAY' : 'HOME'}
                                                            </span>
                                                            <span className="text-white font-bold tracking-tight">{p.name}</span>
                                                        </div>
                                                        <Award className="w-3.5 h-3.5 text-accent-blue opacity-0 group-hover/pcard:opacity-100 transition-opacity" />
                                                    </div>
                                                    <div className="flex items-center gap-4">
                                                        <div className="text-center">
                                                            <div className="text-[8px] text-gray-600 font-bold uppercase tracking-widest mb-0.5">PTS</div>
                                                            <div className="text-sm font-black text-white">{p.pts}</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-[8px] text-gray-600 font-bold uppercase tracking-widest mb-0.5">REB</div>
                                                            <div className="text-sm font-black text-gray-400">{p.reb}</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-[8px] text-gray-600 font-bold uppercase tracking-widest mb-0.5">AST</div>
                                                            <div className="text-sm font-black text-gray-400">{p.ast}</div>
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
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/60 backdrop-blur-md">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="glass relative w-full max-w-2xl bg-[#0b0c10] border border-white/10 rounded-[44px] overflow-hidden shadow-2xl"
                        >
                            <button
                                onClick={() => setSelectedPlayer(null)}
                                className="absolute top-8 right-8 w-10 h-10 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white/40 hover:text-white transition-colors z-10"
                            >
                                <X className="w-5 h-5" />
                            </button>

                            <div className="p-12">
                                <div className="flex items-center gap-6 mb-12">
                                    <div className={cn(
                                        "w-24 h-24 rounded-[32px] overflow-hidden flex items-center justify-center text-4xl font-black text-white relative shadow-2xl",
                                        selectedPlayer.team_label === 'A' ? "bg-gradient-to-br from-accent-blue/30 to-accent-blue/5" : "bg-gradient-to-br from-accent-orange/30 to-accent-orange/5"
                                    )}>
                                        {selectedPlayer.id && selectedPlayer.league === 'nba' ? (
                                            <img
                                                src={`https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/${selectedPlayer.id}.png`}
                                                alt={selectedPlayer.name}
                                                className="w-full h-full object-cover scale-110"
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).style.display = 'none';
                                                    (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
                                                }}
                                            />
                                        ) : null}
                                        <span className={cn(
                                            selectedPlayer.id && selectedPlayer.league === 'nba' ? "hidden" : ""
                                        )}>
                                            {selectedPlayer.name.charAt(0)}
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex items-center gap-3">
                                            <span className={cn("px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-tighter", selectedPlayer.team_label === 'A' ? "bg-accent-blue/20 text-accent-blue" : "bg-accent-orange/20 text-accent-orange")}>
                                                {selectedPlayer.team_label === 'A' ? 'AWAY' : 'HOME'}
                                            </span>
                                            <h2 className="text-3xl font-black text-white tracking-tighter leading-none">{selectedPlayer.name}</h2>
                                        </div>
                                        <div className="text-sm text-gray-500 font-bold uppercase tracking-widest">Model Intelligence Projection</div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-3 gap-8 mb-12">
                                    <div className="p-8 rounded-[32px] bg-white/[0.02] border border-white/[0.04] text-center space-y-2">
                                        <div className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">Predicted Pts</div>
                                        <div className="text-4xl font-black text-white tracking-tighter">{selectedPlayer.pts}</div>
                                    </div>
                                    <div className="p-8 rounded-[32px] bg-white/[0.02] border border-white/[0.04] text-center space-y-2">
                                        <div className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">Predicted Reb</div>
                                        <div className="text-4xl font-black text-gray-300 tracking-tighter">{selectedPlayer.reb}</div>
                                    </div>
                                    <div className="p-8 rounded-[32px] bg-white/[0.02] border border-white/[0.04] text-center space-y-2">
                                        <div className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">Predicted Ast</div>
                                        <div className="text-4xl font-black text-gray-300 tracking-tighter">{selectedPlayer.ast}</div>
                                    </div>
                                </div>

                                <div className="space-y-6">
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-[10px] font-bold text-accent-blue uppercase tracking-widest">Usage Vacuum Redistribution</h3>
                                        <Activity className="w-4 h-4 text-accent-blue opacity-50" />
                                    </div>
                                    <div className="space-y-4">
                                        {selectedPlayer.trace.map((tr, idx) => (
                                            <div key={idx} className="flex items-center justify-between p-5 rounded-2xl bg-white/[0.01] border border-white/[0.04] transition-all hover:bg-white/[0.02]">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-2 h-2 rounded-full bg-accent-blue" />
                                                    <span className="text-[11px] font-bold text-gray-400 text-nowrap">{tr.split(":")[0]}</span>
                                                </div>
                                                <span className="text-[11px] font-mono font-black text-white">{tr.split(":")[1] || ""}</span>
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
