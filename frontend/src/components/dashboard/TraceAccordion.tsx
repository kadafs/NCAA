"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Info, Calculator, BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { GameFactor } from "@/types";

interface TraceAccordionProps {
    trace: string[];
    factors: GameFactor[];
    defaultOpen?: boolean;
}

/**
 * TraceAccordion - Expandable math/factor breakdown
 * 
 * Displays model trace and factor analysis:
 * - Collapsible header with expand/collapse animation
 * - List of trace steps (calculation breakdown)
 * - Factor bars showing impact (positive/negative)
 * 
 * Mobile: Default collapsed to save space
 * Desktop: Can default open
 */
export function TraceAccordion({ trace, factors, defaultOpen = false }: TraceAccordionProps) {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    return (
        <div className="bg-dash-card border border-dash-border rounded-2xl overflow-hidden">
            {/* Header - Always visible */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-4 hover:bg-dash-card-hover transition-colors"
                aria-expanded={isOpen}
                aria-controls="trace-content"
            >
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-gold/10 rounded-lg flex items-center justify-center">
                        <Calculator className="w-4 h-4 text-gold" />
                    </div>
                    <div className="text-left">
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                            Model Trace
                        </h4>
                        <p className="text-[10px] text-dash-text-muted mt-0.5">
                            View calculation breakdown
                        </p>
                    </div>
                </div>
                <motion.div
                    animate={{ rotate: isOpen ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                >
                    <ChevronDown className="w-5 h-5 text-dash-text-muted" />
                </motion.div>
            </button>

            {/* Expandable Content */}
            <AnimatePresence initial={false}>
                {isOpen && (
                    <motion.div
                        id="trace-content"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className="overflow-hidden"
                    >
                        <div className="px-4 pb-4 space-y-6">
                            {/* Trace Steps */}
                            <div className="space-y-3">
                                <div className="flex items-center gap-2 text-[10px] font-bold text-dash-text-muted uppercase tracking-wider">
                                    <Info className="w-3 h-3" />
                                    Calculation Steps
                                </div>
                                <div className="space-y-2 pl-2 border-l-2 border-dash-border">
                                    {trace.map((step, idx) => (
                                        <motion.p
                                            key={idx}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            className="text-[11px] text-dash-text-secondary leading-relaxed pl-3"
                                        >
                                            {step}
                                        </motion.p>
                                    ))}
                                </div>
                            </div>

                            {/* Factor Bars */}
                            <div className="space-y-3">
                                <div className="flex items-center gap-2 text-[10px] font-bold text-dash-text-muted uppercase tracking-wider">
                                    <BarChart2 className="w-3 h-3" />
                                    Impact Factors
                                </div>
                                <div className="space-y-2">
                                    {factors.map((factor, idx) => (
                                        <FactorBar key={factor.label} factor={factor} delay={idx * 0.05} />
                                    ))}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

interface FactorBarProps {
    factor: GameFactor;
    delay?: number;
}

function FactorBar({ factor, delay = 0 }: FactorBarProps) {
    const barColor =
        factor.impact === "positive" ? "bg-dash-success" :
            factor.impact === "negative" ? "bg-dash-danger" : "bg-dash-text-muted";

    const textColor =
        factor.impact === "positive" ? "text-dash-success" :
            factor.impact === "negative" ? "text-dash-danger" : "text-dash-text-muted";

    return (
        <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay }}
            className="flex items-center gap-3"
        >
            <span className="text-[10px] font-bold text-dash-text-secondary w-28 truncate">
                {factor.label}
            </span>
            <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                    className={cn("h-full rounded-full", barColor)}
                    initial={{ width: 0 }}
                    animate={{ width: `${factor.value}%` }}
                    transition={{ duration: 0.6, delay: delay + 0.1, ease: "easeOut" }}
                />
            </div>
            <span className={cn("text-[10px] font-bold w-8 text-right", textColor)}>
                {factor.value}%
            </span>
        </motion.div>
    );
}
