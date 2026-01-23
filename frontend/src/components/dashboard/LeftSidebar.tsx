"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
    User,
    BarChart2,
    Settings,
    Layers,
    PieChart,
    Activity,
    TrendingUp,
    Award
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
    icon: React.ElementType;
    label: string;
    href: string;
}

const NAV_ITEMS: NavItem[] = [
    { icon: User, label: "Profile", href: "/dashboard" },
    { icon: BarChart2, label: "Analytics", href: "/dashboard/analytics" },
    { icon: Activity, label: "Live", href: "/dashboard/live" },
    { icon: PieChart, label: "Props", href: "/dashboard/props" },
    { icon: TrendingUp, label: "Trends", href: "/dashboard/trends" },
    { icon: Award, label: "Performance", href: "/performance" },
    { icon: Layers, label: "History", href: "/history" },
    { icon: Settings, label: "Settings", href: "/dashboard/settings" },
];

/**
 * LeftSidebar - Icon-based navigation sidebar
 * 
 * Displays vertical icon navigation matching reference design:
 * - Fixed left position on desktop (lg+)
 * - Hidden on mobile (use bottom nav instead)
 * - Active state highlighting with gold accent
 * - Hover tooltips for icon labels
 * 
 * Mobile: Completely hidden, replaced by BottomNav
 */
export function LeftSidebar() {
    const pathname = usePathname();

    return (
        <aside className="hidden lg:flex fixed left-0 top-0 h-screen w-16 xl:w-20 bg-dash-bg border-r border-dash-border flex-col items-center py-8 z-40">
            {/* Logo / Brand */}
            <div className="mb-8">
                <div className="w-10 h-10 bg-gold rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(251,191,36,0.3)]">
                    <span className="text-dash-bg font-black text-lg">B</span>
                </div>
            </div>

            {/* Navigation Icons */}
            <nav className="flex-1 flex flex-col items-center gap-2">
                {NAV_ITEMS.map((item) => {
                    const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                    const Icon = item.icon;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className="group relative"
                        >
                            <motion.div
                                className={cn(
                                    "w-10 h-10 xl:w-12 xl:h-12 rounded-xl flex items-center justify-center transition-all",
                                    isActive
                                        ? "bg-gold/10 text-gold"
                                        : "text-dash-text-muted hover:text-white hover:bg-dash-card"
                                )}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <Icon className="w-5 h-5" />

                                {/* Active indicator */}
                                {isActive && (
                                    <motion.div
                                        className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-gold rounded-r-full"
                                        layoutId="activeIndicator"
                                    />
                                )}
                            </motion.div>

                            {/* Tooltip */}
                            <div className="absolute left-full ml-3 top-1/2 -translate-y-1/2 px-3 py-1.5 bg-dash-card border border-dash-border rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all whitespace-nowrap z-50">
                                <span className="text-[10px] font-bold text-white uppercase tracking-wider">
                                    {item.label}
                                </span>
                                <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 w-2 h-2 bg-dash-card border-l border-b border-dash-border rotate-45" />
                            </div>
                        </Link>
                    );
                })}
            </nav>

            {/* Bottom Profile Icon */}
            <div className="mt-auto pt-4 border-t border-dash-border">
                <button className="w-10 h-10 rounded-full bg-dash-card border border-dash-border flex items-center justify-center hover:border-gold/50 transition-colors">
                    <span className="text-xs font-bold text-dash-text-muted">MK</span>
                </button>
            </div>
        </aside>
    );
}

/**
 * BottomNav - Mobile bottom navigation bar
 * 
 * Replaces sidebar on mobile devices:
 * - Fixed bottom position
 * - 4-5 main navigation items
 * - 44x44px touch targets
 * - Visible only on mobile (< lg breakpoint)
 */
interface BottomNavProps {
    activeTab?: string;
    onTabChange?: (tab: string) => void;
}

const BOTTOM_NAV_ITEMS = [
    { id: "home", icon: Layers, label: "Home" },
    { id: "props", icon: PieChart, label: "Props" },
    { id: "live", icon: Activity, label: "Live" },
    { id: "performance", icon: TrendingUp, label: "Trust" },
];

export function BottomNav({ activeTab = "home", onTabChange }: BottomNavProps) {
    return (
        <nav className="fixed bottom-0 left-0 right-0 h-16 bg-dash-bg/95 backdrop-blur-xl border-t border-dash-border lg:hidden flex items-center justify-around px-4 z-50 safe-area-pb">
            {BOTTOM_NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;

                return (
                    <button
                        key={item.id}
                        onClick={() => onTabChange?.(item.id)}
                        className={cn(
                            "flex flex-col items-center justify-center gap-1 min-w-[44px] min-h-[44px] transition-colors",
                            isActive ? "text-gold" : "text-dash-text-muted"
                        )}
                        aria-label={item.label}
                    >
                        <Icon className="w-5 h-5" />
                        <span className="text-[8px] font-black uppercase tracking-tight">
                            {item.label}
                        </span>
                    </button>
                );
            })}
        </nav>
    );
}
