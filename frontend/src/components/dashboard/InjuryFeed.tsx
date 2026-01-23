"use client";

import React from "react";
import { motion } from "framer-motion";
import { InjuryEntry } from "@/types";
import { cn } from "@/lib/utils";
import { AlertCircle, ArrowDown, ArrowUp, Clock } from "lucide-react";

interface InjuryFeedProps {
    injuries: InjuryEntry[];
}

export function InjuryFeed({ injuries }: InjuryFeedProps) {
    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between mb-2">
                <h3 className="text-[11px] font-black text-white uppercase tracking-widest flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-dash-danger" />
                    Live Injury Stream
                </h3>
                <span className="text-[9px] font-bold text-dash-text-muted flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Updated 2m ago
                </span>
            </div>

            <div className="space-y-3">
                {injuries.map((injury) => (
                    <motion.div
                        key={injury.id}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="bg-dash-card border-l-2 border-l-dash-danger border border-dash-border p-3 rounded-r-xl group cursor-pointer hover:bg-dash-card-hover transition-colors"
                    >
                        <div className="flex justify-between items-start mb-1">
                            <div>
                                <h4 className="text-[11px] font-black text-white uppercase leading-none group-hover:text-gold transition-colors">{injury.player}</h4>
                                <p className="text-[9px] font-bold text-dash-text-muted mt-1 uppercase">{injury.teamCode} • {injury.status}</p>
                            </div>
                            <div className={cn(
                                "flex items-center gap-0.5 text-[10px] font-black px-1.5 py-0.5 rounded",
                                injury.impactScore < 0 ? "bg-dash-danger/10 text-dash-danger" : "bg-dash-success/10 text-dash-success"
                            )}>
                                {injury.impactScore < 0 ? <ArrowDown className="w-2.5 h-2.5" /> : <ArrowUp className="w-2.5 h-2.5" />}
                                {Math.abs(injury.impactScore).toFixed(1)}
                            </div>
                        </div>
                        <p className="text-[10px] text-dash-text-secondary leading-normal mt-2">
                            {injury.description}
                        </p>
                    </motion.div>
                ))}
            </div>

            <button className="w-full py-2.5 bg-dash-bg-secondary border border-dash-border rounded-xl text-[9px] font-black text-dash-text-muted uppercase hover:text-white transition-colors mt-2">
                View All Active Injuries
            </button>
        </div>
    );
}
