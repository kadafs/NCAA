import React from "react";
import { cn } from "@/lib/utils";
import { ShieldAlert, ShieldCheck, Shield, X } from "lucide-react";

interface ConfidenceBadgeProps {
    confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'NO PLAY' | 'lock' | 'strong' | 'lean' | 'TIER A' | 'TIER B' | 'LEAN' | 'PASS';
    className?: string;
}

export function ConfidenceBadge({ confidence, className }: ConfidenceBadgeProps) {
    const config = {
        HIGH: {
            label: "HIGH CONFIDENCE",
            icon: ShieldAlert,
            bg: "bg-red-500/10",
            text: "text-red-500",
            border: "border-red-500/20"
        },
        MEDIUM: {
            label: "MEDIUM VALUE",
            icon: ShieldCheck,
            bg: "bg-gold/10",
            text: "text-gold",
            border: "border-gold/20"
        },
        LOW: {
            label: "LOW CONFIDENCE",
            icon: Shield,
            bg: "bg-cyan/10",
            text: "text-cyan",
            border: "border-cyan/20"
        },
        "NO PLAY": {
            label: "NO PLAY",
            icon: X,
            bg: "bg-dash-bg-secondary",
            text: "text-dash-text-muted",
            border: "border-dash-border"
        },
        lock: {
            label: "Lock Plays",
            icon: ShieldAlert,
            bg: "bg-red-500/10",
            text: "text-red-500",
            border: "border-red-500/20"
        },
        strong: {
            label: "Strong Play",
            icon: ShieldCheck,
            bg: "bg-gold/10",
            text: "text-gold",
            border: "border-gold/20"
        },
        lean: {
            label: "Model Lean",
            icon: Shield,
            bg: "bg-cyan/10",
            text: "text-cyan",
            border: "border-cyan/20"
        },
        "TIER A": {
            label: "TIER A (HIGH)",
            icon: ShieldAlert,
            bg: "bg-red-500/10",
            text: "text-red-500",
            border: "border-red-500/20"
        },
        "TIER B": {
            label: "TIER B (MID)",
            icon: ShieldCheck,
            bg: "bg-gold/10",
            text: "text-gold",
            border: "border-gold/20"
        },
        "LEAN": {
            label: "LEAN (LOW)",
            icon: Shield,
            bg: "bg-cyan/10",
            text: "text-cyan",
            border: "border-cyan/20"
        },
        "PASS": {
            label: "PASS",
            icon: X,
            bg: "bg-dash-bg-secondary",
            text: "text-dash-text-muted",
            border: "border-dash-border"
        }
    };

    const target = config[confidence] || config.lean;
    const { label, icon: Icon, bg, text, border } = target;

    return (
        <div className={cn(
            "inline-flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-0.5 sm:py-1 rounded-full border text-[9px] sm:text-[10px] font-black uppercase tracking-widest transition-smooth whitespace-nowrap",
            bg, text, border, className
        )}>
            <Icon className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
            <span className="hidden sm:inline">{label}</span>
            <span className="sm:hidden">{label.split(' ')[0]}</span>
        </div>
    );
}
