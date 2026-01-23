"use client";

import React from "react";
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area,
    ReferenceDot
} from "recharts";

interface ForecastLineChartProps {
    data: { time: string; awayVal: number; homeVal: number }[];
    height?: number;
    showAnnotations?: boolean;
    awayLabel?: string;
    homeLabel?: string;
}

/**
 * ForecastLineChart - Wavy line forecast visualization
 * 
 * Features matching reference design:
 * - Smooth curve styling with type="monotone"
 * - Gold (#FBBF24) and cyan (#06B6D4) color scheme
 * - Gradient fills below lines
 * - Optional +% annotation markers at end points
 * 
 * Mobile: Full width, slightly reduced height
 */
export function ForecastLineChart({
    data,
    height = 240,
    showAnnotations = true,
    awayLabel,
    homeLabel
}: ForecastLineChartProps) {
    // Calculate change percentages for annotations
    const lastPoint = data[data.length - 1];
    const firstPoint = data[0];

    const awayChange = lastPoint && firstPoint
        ? ((lastPoint.awayVal - firstPoint.awayVal) / firstPoint.awayVal * 100).toFixed(0)
        : "0";
    const homeChange = lastPoint && firstPoint
        ? ((lastPoint.homeVal - firstPoint.homeVal) / firstPoint.homeVal * 100).toFixed(0)
        : "0";

    return (
        <div className="w-full relative" style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 20, right: 30, bottom: 10, left: 0 }}>
                    <defs>
                        <linearGradient id="colorAwayCyan" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.15} />
                            <stop offset="95%" stopColor="#06B6D4" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorHomeGold" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#FBBF24" stopOpacity={0.15} />
                            <stop offset="95%" stopColor="#FBBF24" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="rgba(255,255,255,0.03)"
                    />
                    <XAxis
                        dataKey="time"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 9, fill: "#64748B", fontWeight: 700 }}
                        dy={10}
                    />
                    <YAxis
                        hide
                        domain={['auto', 'auto']}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: "#161920",
                            borderColor: "rgba(255,255,255,0.1)",
                            borderRadius: "16px",
                            fontSize: "10px",
                            fontWeight: 700,
                            color: "#fff",
                            padding: "12px"
                        }}
                        itemStyle={{ color: "#fff" }}
                        labelStyle={{ color: "#94A3B8", fontSize: "9px", marginBottom: "4px" }}
                    />
                    <Area
                        type="monotone"
                        dataKey="awayVal"
                        name={awayLabel || "Away"}
                        stroke="#06B6D4"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorAwayCyan)"
                        animationDuration={1500}
                        dot={false}
                        activeDot={{ r: 6, stroke: "#06B6D4", strokeWidth: 2, fill: "#161920" }}
                    />
                    <Area
                        type="monotone"
                        dataKey="homeVal"
                        name={homeLabel || "Home"}
                        stroke="#FBBF24"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorHomeGold)"
                        animationDuration={1500}
                        dot={false}
                        activeDot={{ r: 6, stroke: "#FBBF24", strokeWidth: 2, fill: "#161920" }}
                    />
                </AreaChart>
            </ResponsiveContainer>

            {/* Annotation Labels - positioned at bottom right */}
            {showAnnotations && (
                <div className="absolute bottom-2 right-4 flex items-center gap-4">
                    <div className="flex items-center gap-1">
                        <span className="text-xs font-bold text-gold">
                            {Number(homeChange) >= 0 ? "+" : ""}{homeChange}%
                        </span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="text-xs font-bold text-cyan">
                            {Number(awayChange) >= 0 ? "+" : ""}{awayChange}%
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}

/**
 * ForecastHeader - Title section for forecast charts
 */
interface ForecastHeaderProps {
    title: string;
    subtitle?: string;
}

export function ForecastHeader({ title, subtitle }: ForecastHeaderProps) {
    return (
        <div className="mb-4">
            <h3 className="text-sm md:text-base font-bold text-white">{title}</h3>
            {subtitle && (
                <p className="text-[10px] text-dash-text-muted mt-0.5">{subtitle}</p>
            )}
        </div>
    );
}

