"use client";

import React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

const LEAGUES = [
    { id: "nba", name: "NBA", fullName: "National Basketball Association" },
    { id: "ncaa", name: "NCAA", fullName: "College Basketball" },
];

interface LeagueSwitcherProps {
    currentLeague: string;
}

export function LeagueSwitcher({ currentLeague }: LeagueSwitcherProps) {
    return (
        <div className="flex items-center gap-1.5 p-1 rounded-2xl border border-white/[0.04] bg-white/[0.02]">
            {LEAGUES.map(l => (
                <Link
                    key={l.id}
                    href={`/dashboard/${l.id}`}
                    className={cn(
                        "px-5 py-2 rounded-xl text-xs font-semibold tracking-tight transition-all duration-300",
                        currentLeague === l.id
                            ? "bg-white/10 text-white shadow-sm ring-1 ring-white/5"
                            : "text-gray-500 hover:text-gray-300 hover:bg-white/[0.04]"
                    )}
                >
                    {l.name}
                </Link>
            ))}
        </div>
    );
}
