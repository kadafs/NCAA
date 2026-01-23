"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
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
    { href: "/dashboard", label: "Dashboard" },
    { href: "/predictions", label: "Predictions" },
    { href: "/stats", label: "Stats" },
    { href: "/performance", label: "Performance" },
];

export function Header() {
    const pathname = usePathname();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [leagueDropdownOpen, setLeagueDropdownOpen] = useState(false);

    // Determine current league from path
    const currentLeague = LEAGUES.find(l => pathname.includes(l.id)) || LEAGUES[0];

    return (
        <header className="w-full bg-dash-bg-secondary border-b border-dash-border sticky top-0 z-50">
            {/* 1. Top League Logo Bar */}
            <div className="bg-dash-bg border-b border-dash-border py-1.5">
                <div className="max-w-7xl mx-auto px-4 flex items-center justify-center sm:justify-between">
                    <div className="flex items-center gap-6 overflow-x-auto no-scrollbar py-1">
                        {LEAGUES.map((league) => (
                            <Link
                                key={league.id}
                                href={`/dashboard?league=${league.id}`}
                                className={cn(
                                    "flex items-center gap-2 px-2 py-1 rounded transition-all",
                                    currentLeague.id === league.id
                                        ? "opacity-100 scale-105"
                                        : "opacity-40 hover:opacity-80 scale-100 grayscale hover:grayscale-0"
                                )}
                            >
                                <div className={cn(
                                    "w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold text-white shadow-sm",
                                    league.id === "nba" ? "bg-red-600" :
                                        league.id === "ncaa" ? "bg-blue-800" : "bg-orange-500"
                                )}>
                                    {league.name[0]}
                                </div>
                                <span className="text-[10px] font-bold tracking-tighter uppercase text-dash-text-secondary">
                                    {league.name}
                                </span>
                            </Link>
                        ))}
                    </div>
                </div>
            </div>

            {/* 2. Brand Nav Row */}
            <div className="border-b border-gray-100">
                <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
                    <div className="flex items-center gap-12">
                        {/* Logo */}
                        <Link href="/" className="flex items-center gap-2 group">
                            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center transform group-hover:rotate-12 transition-transform">
                                <svg viewBox="0 0 40 40" className="w-6 h-6">
                                    <circle cx="20" cy="20" r="16" fill="white" />
                                    <path d="M 12 20 Q 20 12, 28 20" stroke="#E85D04" strokeWidth="2.5" fill="none" />
                                    <path d="M 12 20 Q 20 28, 28 20" stroke="#E85D04" strokeWidth="2.5" fill="none" />
                                </svg>
                            </div>
                            <span className="text-xl font-black text-white tracking-tight">
                                blow<span className="text-gold italic">rout</span>
                            </span>
                        </Link>

                        {/* Desktop Links */}
                        <div className="hidden lg:flex items-center gap-1 h-14">
                            {NAV_LINKS.map((link) => {
                                const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
                                return (
                                    <Link
                                        key={link.href}
                                        href={link.href}
                                        className={cn(
                                            "relative h-14 flex items-center px-4 text-xs font-bold uppercase tracking-wider transition-all",
                                            isActive ? "text-primary" : "text-gray-500 hover:text-navy"
                                        )}
                                    >
                                        {link.label}
                                        {isActive && (
                                            <motion.div
                                                layoutId="activeNav"
                                                className="absolute bottom-0 left-0 right-0 h-1 bg-primary"
                                            />
                                        )}
                                    </Link>
                                );
                            })}
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <button className="hidden sm:flex items-center gap-2 px-6 py-2 border border-gray-200 rounded-full text-xs font-bold uppercase tracking-widest text-navy hover:bg-bg-subtle transition-colors">
                            Log In
                        </button>

                        {/* Mobile Toggle */}
                        <button
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="lg:hidden p-2 text-navy"
                        >
                            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                        </button>
                    </div>
                </div>
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
                                    ? "bg-gold/10 text-gold"
                                    : "text-dash-text-primary hover:bg-dash-card"
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
        </header>
    );
}
