"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import Image from "next/image";

const LEAGUES = [
    { id: "nba", name: "NBA", fullName: "National Basketball Association" },
    { id: "ncaa", name: "NCAA", fullName: "College Basketball" },
    { id: "euro", name: "EURO", fullName: "European Leagues" },
];

const NAV_LINKS = [
    { href: "/", label: "Home" },
    { href: "/dashboard/nba", label: "Games" },
    { href: "/predictions", label: "Predictions" },
    { href: "/stats", label: "Stats" },
    { href: "/standings", label: "Standings" },
];

export function Header() {
    const pathname = usePathname();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [leagueDropdownOpen, setLeagueDropdownOpen] = useState(false);

    // Determine current league from path
    const currentLeague = LEAGUES.find(l => pathname.includes(l.id)) || LEAGUES[0];

    return (
        <header className="bg-white border-b border-border sticky top-0 z-50">
            {/* Top Bar */}
            <div className="bg-navy text-white py-2">
                <div className="max-w-7xl mx-auto px-4 flex items-center justify-between text-xs">
                    <span className="font-medium opacity-80">Advance Basketball Prediction</span>
                    <div className="flex items-center gap-4">
                        <span className="hidden sm:block opacity-60">v2.0 Framework Active</span>
                    </div>
                </div>
            </div>

            {/* Main Navigation */}
            <nav className="max-w-7xl mx-auto px-4">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-3 shrink-0">
                        <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
                            <svg viewBox="0 0 40 40" className="w-8 h-8">
                                <circle cx="20" cy="20" r="16" fill="#E85D04" />
                                <path d="M 4 20 Q 20 15, 36 20" stroke="#1A202C" strokeWidth="1.5" fill="none" />
                                <path d="M 4 20 Q 20 25, 36 20" stroke="#1A202C" strokeWidth="1.5" fill="none" />
                                <line x1="20" y1="4" x2="20" y2="36" stroke="#1A202C" strokeWidth="1.5" />
                            </svg>
                        </div>
                        <span className="text-xl font-extrabold text-display">
                            blow<span className="text-primary">rout</span>
                        </span>
                    </Link>

                    {/* Desktop Navigation */}
                    <div className="hidden md:flex items-center gap-1">
                        {NAV_LINKS.map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                className={cn(
                                    "px-4 py-5 text-sm font-semibold transition-colors border-b-3 border-transparent",
                                    pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href))
                                        ? "text-primary border-primary"
                                        : "text-text-dark hover:text-primary"
                                )}
                            >
                                {link.label}
                            </Link>
                        ))}

                        {/* League Selector */}
                        <div className="relative ml-2">
                            <button
                                onClick={() => setLeagueDropdownOpen(!leagueDropdownOpen)}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-text-dark hover:text-primary transition-colors rounded-lg hover:bg-bg-subtle"
                            >
                                {currentLeague.name}
                                <ChevronDown className={cn("w-4 h-4 transition-transform", leagueDropdownOpen && "rotate-180")} />
                            </button>

                            {leagueDropdownOpen && (
                                <div className="absolute top-full right-0 mt-1 w-56 bg-white rounded-lg shadow-lg border border-border py-2 z-50">
                                    {LEAGUES.map((league) => (
                                        <Link
                                            key={league.id}
                                            href={`/dashboard/${league.id}`}
                                            onClick={() => setLeagueDropdownOpen(false)}
                                            className={cn(
                                                "block px-4 py-3 hover:bg-bg-subtle transition-colors",
                                                currentLeague.id === league.id && "bg-bg-subtle"
                                            )}
                                        >
                                            <div className="font-semibold text-text-dark">{league.name}</div>
                                            <div className="text-xs text-text-muted">{league.fullName}</div>
                                        </Link>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Mobile Menu Button */}
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="md:hidden p-2 text-text-dark hover:text-primary"
                    >
                        {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                    </button>
                </div>

                {/* Mobile Navigation */}
                {mobileMenuOpen && (
                    <div className="md:hidden border-t border-border py-4 space-y-1">
                        {NAV_LINKS.map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                onClick={() => setMobileMenuOpen(false)}
                                className={cn(
                                    "block px-4 py-3 text-sm font-semibold rounded-lg transition-colors",
                                    pathname === link.href
                                        ? "bg-primary/10 text-primary"
                                        : "text-text-dark hover:bg-bg-subtle"
                                )}
                            >
                                {link.label}
                            </Link>
                        ))}

                        <div className="border-t border-border mt-3 pt-3">
                            <div className="px-4 text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">
                                Select League
                            </div>
                            {LEAGUES.map((league) => (
                                <Link
                                    key={league.id}
                                    href={`/dashboard/${league.id}`}
                                    onClick={() => setMobileMenuOpen(false)}
                                    className={cn(
                                        "block px-4 py-3 rounded-lg transition-colors",
                                        currentLeague.id === league.id ? "bg-bg-subtle" : "hover:bg-bg-subtle"
                                    )}
                                >
                                    <div className="font-semibold text-text-dark">{league.name}</div>
                                    <div className="text-xs text-text-muted">{league.fullName}</div>
                                </Link>
                            ))}
                        </div>
                    </div>
                )}
            </nav>
        </header>
    );
}
