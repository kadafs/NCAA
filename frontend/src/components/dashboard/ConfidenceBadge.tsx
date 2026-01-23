import React from "react";
import { cn } from "@/lib/utils";
import { ShieldAlert, ShieldCheck, Shield } from "lucide-react";

interface ConfidenceBadgeProps {
    confidence: 'lock' | 'strong' | 'lean';
    className?: string;
}

export function ConfidenceBadge({ confidence, className }: ConfidenceBadgeProps) {
    const config = {
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

    const { label, icon: Icon, bg, text, border } = config[confidence];

    return (
        <div className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[10px] font-black uppercase tracking-widest",
            bg, text, border, className
        )}>
            <Icon className="w-3 h-3" />
            {label}
        </div>
    );
}
