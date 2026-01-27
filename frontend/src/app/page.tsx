"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Trophy,
  ChevronRight,
  Zap,
  Target,
  BarChart3,
  TrendingUp,
  Award,
  Shield,
  Activity,
  Users,
  ArrowUpRight,
  Play
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

/**
 * Landing Page - Dark Theme Redesign
 * 
 * Matches the reference design with:
 * - Dark navy background (#0B0D11)
 * - Gold (#FBBF24) and cyan (#06B6D4) accents
 * - Rounded cards with subtle borders
 * - Smooth animations
 * - Mobile-first responsive design
 */

const LEAGUES = [
  {
    id: "nba",
    name: "NBA",
    fullName: "National Basketball Association",
    icon: Zap,
    accentColor: "gold",
    gamesCount: 12,
    description: "Real-time prop predictions with star player usage analytics.",
  },
  {
    id: "ncaa",
    name: "NCAA",
    fullName: "Division I Basketball",
    icon: Trophy,
    accentColor: "cyan",
    gamesCount: 24,
    description: "Advanced efficiency metrics for 350+ D1 programs.",
  },
];

const PLATFORM_STATS = [
  { value: "84.2%", label: "Win Rate", sublabel: "O/U Predictions" },
  { value: "12.4%", label: "ROI", sublabel: "All Markets" },
  { value: "2,400+", label: "Games", sublabel: "This Season" },
  { value: "142-98", label: "Record", sublabel: "Season to Date" },
];

const FEATURES = [
  {
    icon: Target,
    title: "Precision Modeling",
    description: "Proprietary algorithms analyzing 50+ factors per game including pace, efficiency, and situational adjustments.",
  },
  {
    icon: BarChart3,
    title: "Real-Time Edge Detection",
    description: "Live odds comparison across 8+ sportsbooks with instant line movement alerts and value identification.",
  },
  {
    icon: TrendingUp,
    title: "Transparent Performance",
    description: "Every prediction tracked and verified. Full trace logs showing exactly how our models reach conclusions.",
  },
];

const LIVE_GAMES = [
  { id: "1", away: "LAL", home: "BOS", awayScore: 102, homeScore: 108, quarter: "Q4", time: "2:34", league: "NBA", edge: "+3.2" },
  { id: "2", away: "DUKE", home: "UNC", awayScore: 68, homeScore: 71, quarter: "2H", time: "8:45", league: "NCAA", edge: "+5.1" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-dash-bg text-dash-text-primary">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-dash-bg/80 backdrop-blur-xl border-b border-dash-border">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gold rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(251,191,36,0.3)]">
              <span className="text-dash-bg font-black text-lg">B</span>
            </div>
            <span className="text-xl font-black text-white tracking-tighter uppercase">
              blow<span className="text-gold italic">rout</span>
            </span>
          </Link>

          {/* Nav Links - Desktop */}
          <div className="hidden md:flex items-center gap-8">
            {["Dashboard", "Props", "Performance", "History"].map((item) => (
              <Link
                key={item}
                href={`/${item.toLowerCase()}`}
                className="text-xs font-bold text-dash-text-muted uppercase tracking-widest hover:text-white transition-colors"
              >
                {item}
              </Link>
            ))}
          </div>

          {/* CTA */}
          <Link
            href="/dashboard"
            className="px-5 py-2.5 bg-gold text-dash-bg text-xs font-black uppercase tracking-widest rounded-xl hover:scale-105 transition-transform shadow-[0_0_20px_rgba(251,191,36,0.2)]"
          >
            Launch App
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-32 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-20 -right-40 w-96 h-96 bg-gold/5 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 -left-40 w-96 h-96 bg-cyan/5 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center max-w-4xl mx-auto"
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-dash-card border border-dash-border rounded-full mb-8">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-[10px] font-bold text-dash-text-secondary uppercase tracking-widest">
                Live Predictions Active
              </span>
            </div>

            {/* Tagline */}
            <p className="text-base md:text-lg text-dash-text-muted max-w-2xl mx-auto mb-10 leading-relaxed">
              The world's most advanced prediction engine for NBA and NCAA basketball.
              Real-time analytics powered by proprietary models with full transparency.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/dashboard"
                className="group flex items-center gap-3 px-8 py-4 bg-gold text-dash-bg font-black uppercase tracking-widest rounded-2xl hover:scale-105 transition-all shadow-[0_0_30px_rgba(251,191,36,0.3)]"
              >
                Launch Dashboard
                <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/performance"
                className="flex items-center gap-3 px-8 py-4 bg-dash-card border border-dash-border text-white font-bold uppercase tracking-widest rounded-2xl hover:border-gold/30 transition-colors"
              >
                <Play className="w-4 h-4" />
                View Performance
              </Link>
            </div>
          </motion.div>

          {/* Stats Row */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="mt-16 md:mt-24 grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6"
          >
            {PLATFORM_STATS.map((stat, idx) => (
              <div
                key={stat.label}
                className="bg-dash-card border border-dash-border rounded-2xl p-4 md:p-6 text-center hover:border-gold/20 transition-colors"
              >
                <div className={cn(
                  "text-2xl md:text-3xl font-black mb-1",
                  idx % 2 === 0 ? "text-gold" : "text-cyan"
                )}>
                  {stat.value}
                </div>
                <div className="text-xs font-bold text-white uppercase">{stat.label}</div>
                <div className="text-[10px] font-medium text-dash-text-muted uppercase">{stat.sublabel}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Live Games Marquee */}
      <section className="py-8 border-y border-dash-border bg-dash-bg-secondary">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              <span className="text-[10px] font-black text-red-500 uppercase tracking-widest">Live</span>
            </div>
            <div className="h-px flex-1 bg-dash-border" />
          </div>

          <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
            {LIVE_GAMES.map((game) => (
              <Link
                key={game.id}
                href={`/dashboard/${game.league.toLowerCase()}`}
                className="flex-shrink-0 bg-dash-card border border-dash-border rounded-2xl p-4 min-w-[200px] hover:border-gold/30 transition-colors group"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[9px] font-black text-gold uppercase tracking-wider">{game.league}</span>
                  <span className="text-[9px] font-bold text-dash-text-muted">{game.quarter} • {game.time}</span>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-bold">
                    <span className="text-dash-text-secondary">{game.away}</span>
                    <span className="text-white">{game.awayScore}</span>
                  </div>
                  <div className="flex justify-between text-xs font-bold">
                    <span className="text-dash-text-secondary">{game.home}</span>
                    <span className="text-white">{game.homeScore}</span>
                  </div>
                </div>
                <div className="mt-3 pt-2 border-t border-dash-border flex items-center justify-between">
                  <span className="text-[9px] font-bold text-dash-text-muted uppercase">Edge</span>
                  <span className="text-xs font-black text-dash-success">{game.edge}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* League Selection Grid */}
      <section className="py-16 md:py-24">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-12">
            <span className="text-[10px] font-black text-gold uppercase tracking-[0.4em] mb-4 inline-block">
              Competitions
            </span>
            <h2 className="text-3xl md:text-5xl font-black text-white uppercase tracking-tighter">
              Choose Your League
            </h2>
            <div className="h-1 w-16 bg-gold mx-auto mt-4" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {LEAGUES.map((league, idx) => (
              <motion.div
                key={league.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
              >
                <Link
                  href={`/dashboard/${league.id}`}
                  className="group block bg-dash-card border border-dash-border rounded-2xl p-6 hover:border-gold/30 hover:scale-[1.02] transition-all h-full"
                >
                  <div className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center mb-4",
                    league.accentColor === "gold" ? "bg-gold/10" : "bg-cyan/10"
                  )}>
                    <league.icon className={cn(
                      "w-6 h-6",
                      league.accentColor === "gold" ? "text-gold" : "text-cyan"
                    )} />
                  </div>
                  <h3 className="text-xl font-black text-white uppercase tracking-tight mb-1">
                    {league.name}
                  </h3>
                  <p className="text-[10px] font-bold text-dash-text-muted uppercase tracking-wider mb-4">
                    {league.fullName}
                  </p>
                  <div className="flex items-center justify-between pt-4 border-t border-dash-border">
                    <span className="text-[10px] font-bold text-dash-text-muted">
                      {league.gamesCount} games today
                    </span>
                    <ArrowUpRight className="w-4 h-4 text-dash-text-muted group-hover:text-gold transition-colors" />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 md:py-24 bg-dash-bg-secondary border-y border-dash-border">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {FEATURES.map((feature, idx) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="bg-dash-card border border-dash-border rounded-3xl p-8 hover:border-gold/20 transition-colors"
              >
                <div className="w-14 h-14 bg-gold/10 rounded-2xl flex items-center justify-center mb-6">
                  <feature.icon className="w-7 h-7 text-gold" />
                </div>
                <h3 className="text-lg font-black text-white uppercase tracking-tight mb-3">
                  {feature.title}
                </h3>
                <p className="text-sm text-dash-text-muted leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 md:py-24">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="bg-gradient-to-br from-gold/20 to-dash-card border border-gold/30 rounded-[32px] p-8 md:p-12"
          >
            <div className="w-16 h-16 bg-gold rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-[0_0_40px_rgba(251,191,36,0.3)]">
              <Target className="w-8 h-8 text-dash-bg" />
            </div>
            <h2 className="text-2xl md:text-4xl font-black text-white uppercase tracking-tighter mb-4">
              Start Winning Today
            </h2>
            <p className="text-dash-text-muted max-w-lg mx-auto mb-8">
              Join thousands of analysts using our platform. Free access to predictions,
              premium unlocks full traces and prop analysis.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/dashboard"
                className="px-8 py-4 bg-gold text-dash-bg font-black uppercase tracking-widest rounded-2xl hover:scale-105 transition-transform"
              >
                Get Started Free
              </Link>
              <Link
                href="/performance"
                className="px-8 py-4 border border-dash-border text-white font-bold uppercase tracking-widest rounded-2xl hover:border-gold/30 transition-colors"
              >
                View Track Record
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-dash-border">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gold rounded-xl flex items-center justify-center">
                <span className="text-dash-bg font-black text-lg">B</span>
              </div>
              <span className="text-xl font-black text-white tracking-tighter uppercase">
                blow<span className="text-gold italic">rout</span>
              </span>
            </div>

            <div className="flex items-center gap-8">
              {["Dashboard", "Props", "Performance", "History"].map((item) => (
                <Link
                  key={item}
                  href={`/${item.toLowerCase()}`}
                  className="text-[10px] font-bold text-dash-text-muted uppercase tracking-widest hover:text-white transition-colors"
                >
                  {item}
                </Link>
              ))}
            </div>

            <p className="text-[10px] font-bold text-dash-text-muted uppercase tracking-wider">
              © 2026 Blowrout. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
