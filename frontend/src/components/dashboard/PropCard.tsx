"use client";

import React from "react";
import { motion } from "framer-motion";
import { PlayerProp } from "@/types";
import { cn } from "@/lib/utils";
import { TrendingUp, User, Zap } from "lucide-react";

interface PropCardProps {
    prop: PlayerProp;
}

export function PropCard({ prop }: PropCardProps) {
    const [imgError, setImgError] = React.useState(false);

    return (
        <motion.div
            whileHover={{ scale: 1.01 }}
            className="group flex flex-col bg-dash-card border border-dash-border rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-[0_8px_32px_rgba(30,30,50,0.4)]"
        >
            <div className="p-4 flex gap-4">
                {/* Headshot & Team */}
                <div className="relative flex-shrink-0">
                    <div className="w-14 h-14 bg-dash-bg-secondary rounded-xl flex items-center justify-center p-1 border border-dash-border overflow-hidden">
                        {prop.image && !imgError ? (
                            <img
                                src={prop.image}
                                alt={prop.name}
                                className="w-full h-full object-cover rounded-md"
                                onError={() => setImgError(true)}
                            />
                        ) : (
                            <User className="w-6 h-6 text-dash-text-muted" />
                        )}
                    </div>
                    <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-dash-card border border-dash-border rounded-lg flex items-center justify-center text-[8px] font-black text-white">
                        {prop.teamCode}
                    </div>
                </div>

                {/* Info */}
                <div className="flex-1 flex flex-col justify-center gap-1">
                    <div className="flex justify-between items-start">
                        <div>
                            <h4 className="text-xs font-black text-white uppercase truncate max-w-[120px]">{prop.name}</h4>
                            <p className="text-[9px] font-bold text-dash-text-muted uppercase leading-none">{prop.position} • {prop.team}</p>
                        </div>
                        {prop.usageBoost && (
                            <div className="bg-gold/90 text-dash-bg text-[7px] font-black px-1.5 py-0.5 rounded-full uppercase tracking-tighter flex items-center gap-0.5">
                                <Zap className="w-2 h-2 fill-current" />
                                Boosted
                            </div>
                        )}
                    </div>

                    <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-[9px] font-black px-2 py-0.5 bg-dash-bg-secondary border border-dash-border rounded text-dash-text-primary uppercase">
                            {prop.propType}
                        </span>
                        <div className="flex-1 h-px bg-dash-border" />
                        <span className="text-xs font-black text-white italic">{prop.line}</span>
                    </div>
                </div>
            </div>

            {/* Prediction Footer */}
            <div className="px-4 py-3 bg-white/5 border-t border-dash-border flex items-center justify-between">
                <div className="flex flex-col">
                    <span className="text-[8px] font-bold text-dash-text-muted uppercase">Model Result</span>
                    <span className="text-sm font-black text-dash-accent-cyan italic">{prop.projection.toFixed(1)}</span>
                </div>

                <div className="text-right flex flex-col items-end">
                    <span className="text-[8px] font-black text-gold uppercase flex items-center gap-1">
                        <TrendingUp className="w-2 h-2" />
                        +{prop.edgePct.toFixed(1)}% Edge
                    </span>
                    <div className="flex gap-0.5 mt-1">
                        {prop.recentTrend.map((v, i) => (
                            <div
                                key={i}
                                className={cn(
                                    "w-3 h-1 rounded-full",
                                    v > 0 ? "bg-dash-success" : "bg-dash-danger"
                                )}
                            />
                        ))}
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
