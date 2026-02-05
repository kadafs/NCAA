"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface CircularGaugeProps {
    value: number;
    max?: number;
    label: string;
    subLabel?: string;
    color?: string; // e.g., "#FBBF24" or "#06B6D4"
    size?: number;
    strokeWidth?: number;
}

export function CircularGauge({
    value,
    max = 100,
    label,
    subLabel,
    color = "#FBBF24",
    size = 140,
    strokeWidth = 10
}: CircularGaugeProps) {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (value / max) * circumference;

    return (
        <div className="flex flex-col items-center justify-center relative" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="transform -rotate-90">
                {/* Background Circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="currentColor"
                    strokeWidth={strokeWidth}
                    fill="transparent"
                    className="text-white/5"
                />
                {/* Progress Circle */}
                <motion.circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={color}
                    strokeWidth={strokeWidth}
                    fill="transparent"
                    strokeDasharray={circumference}
                    initial={{ strokeDashoffset: circumference }}
                    animate={{ strokeDashoffset: offset }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    strokeLinecap="round"
                    className="drop-shadow-[0_0_8px_rgba(255,255,255,0.2)]"
                />
            </svg>

            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className={cn(
                    "font-black text-white leading-none",
                    size <= 64 ? "text-lg" : size <= 80 ? "text-xl" : "text-2xl"
                )}>
                    {value.toFixed(1)}%
                </span>
                <span className={cn(
                    "font-bold text-dash-text-secondary uppercase tracking-widest mt-0.5",
                    size <= 64 ? "text-[8px]" : "text-[10px]"
                )}>
                    {label}
                </span>
                {subLabel && (
                    <span className={cn(
                        "font-medium text-dash-text-muted uppercase",
                        size <= 64 ? "text-[6px]" : "text-[8px]"
                    )}>
                        {subLabel}
                    </span>
                )}
            </div>
        </div>
    );
}
