import React from "react";
import { cn } from "@/lib/utils";
import { ShieldAlert, ShieldCheck, Shield, X } from "lucide-react";

interface ConfidenceBadgeProps {
    confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'NO PLAY' | 'lock' | 'strong' | 'lean';
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
            label: "MODEL LEAN",
            icon: Shield,
            bg: "bg-cyan/10",
            text: "text-cyan",
            border: "border-cyan/20"
        },
        "NO PLAY": {
            label: "NO PLAY",
            icon: X,
            bg: "bg-white/5",
            text: "text-white/40",
            border: "border-white/10"
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
        }
    };

    const target = config[confidence] || config.lean;
    const { label, icon: Icon, bg, text, border } = target;

    return (
        <div className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[10px] font-black uppercase tracking-widest transition-all",
            bg, text, border, className
        )}>
            <Icon className="w-3 h-3" />
            {label}
        </div>
    );
}
