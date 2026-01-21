"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Trophy,
  ChevronRight,
  Zap,
  Target,
  BarChart3,
  TrendingUp,
  Calendar,
  Award,
  ArrowRight
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

const LEAGUES = [
  {
    id: "nba",
    name: "NBA",
    fullName: "National Basketball Association",
    icon: Zap,
    gradient: "from-red-600 to-red-800",
    accentColor: "text-red-600",
    bgAccent: "bg-red-50",
    description: "Real-time prop predictions with star player usage analytics.",
    gamesCount: 12,
  },
  {
    id: "ncaa",
    name: "NCAA",
    fullName: "Division I Basketball",
    icon: Trophy,
    gradient: "from-blue-700 to-blue-900",
    accentColor: "text-blue-700",
    bgAccent: "bg-blue-50",
    description: "Advanced efficiency metrics for 350+ D1 programs.",
    gamesCount: 24,
  },
  {
    id: "euro",
    name: "EURO",
    fullName: "European Leagues",
    icon: Award,
    gradient: "from-orange-500 to-orange-700",
    accentColor: "text-orange-600",
    bgAccent: "bg-orange-50",
    description: "EuroLeague, ACB, and top continental competition predictions.",
    gamesCount: 8,
  }
];

const PLATFORM_FEATURES = [
  {
    icon: Target,
    title: "84.2% Accuracy",
    description: "Verified win rate on O/U predictions",
  },
  {
    icon: BarChart3,
    title: "Real-Time Analytics",
    description: "Live odds tracking and edge detection",
  },
  {
    icon: TrendingUp,
    title: "Advanced Metrics",
    description: "Proprietary efficiency models",
  },
];

const UPCOMING_GAMES = [
  {
    league: "NBA",
    away: "LAL",
    home: "BOS",
    time: "7:30 PM ET",
    prediction: "OVER 228.5",
    edge: "+3.2",
  },
  {
    league: "NCAA",
    away: "DUKE",
    home: "UNC",
    time: "9:00 PM ET",
    prediction: "UNC -4.5",
    edge: "+2.1",
  },
  {
    league: "EURO",
    away: "REAL",
    home: "FENER",
    time: "2:00 PM ET",
    prediction: "UNDER 155.5",
    edge: "+4.7",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg-light">
      {/* Hero Section */}
      <section className="hero-gradient relative overflow-hidden">
        <div className="absolute inset-0 hero-overlay" />

        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-20 left-10 w-32 h-32 border-2 border-white rounded-full" />
          <div className="absolute top-40 right-20 w-48 h-48 border-2 border-white rounded-full" />
          <div className="absolute bottom-10 left-1/3 w-24 h-24 border-2 border-white rounded-full" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 py-20 md:py-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-3xl"
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur px-4 py-2 rounded-full mb-6">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-white/90 text-sm font-medium">v2.0 Framework Active</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold text-white text-display leading-[1.1] mb-6">
              Advance{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-orange-500">
                Basketball
              </span>{" "}
              Prediction
            </h1>

            <p className="text-lg md:text-xl text-white/70 mb-8 max-w-2xl leading-relaxed">
              Professional-grade analytics for NBA, NCAA, and European basketball.
              Our proprietary models deliver 84%+ accuracy on totals and spreads.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap gap-4">
              <Link
                href="/dashboard/nba"
                className="btn-primary inline-flex items-center gap-2 text-lg"
              >
                View Predictions
                <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                href="/history"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur text-white font-semibold rounded-lg hover:bg-white/20 transition-colors"
              >
                Track Record
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Featured Games Section */}
      <section className="py-12 bg-white border-b border-border">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-primary" />
              <h2 className="text-lg font-bold text-text-dark">Today's Top Picks</h2>
            </div>
            <Link
              href="/dashboard/nba"
              className="text-sm font-semibold text-primary hover:underline flex items-center gap-1"
            >
              View All Games
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {UPCOMING_GAMES.map((game, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="game-card p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold text-text-muted uppercase tracking-wide">
                    {game.league}
                  </span>
                  <span className="text-xs text-text-muted">{game.time}</span>
                </div>

                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="text-center">
                      <div className="text-lg font-bold text-text-dark">{game.away}</div>
                    </div>
                    <span className="text-xs text-text-muted font-medium">@</span>
                    <div className="text-center">
                      <div className="text-lg font-bold text-text-dark">{game.home}</div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <span className="text-sm font-bold text-text-dark">{game.prediction}</span>
                  <span className="text-sm font-bold text-success">Edge {game.edge}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* League Selection */}
      <section className="py-16 bg-bg-light">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-text-dark text-display mb-4">
              Select Your League
            </h2>
            <p className="text-text-muted max-w-xl mx-auto">
              Choose from three major basketball leagues with specialized prediction models optimized for each competition.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {LEAGUES.map((league, i) => (
              <motion.div
                key={league.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.1 }}
              >
                <Link href={`/dashboard/${league.id}`} className="block group">
                  <div className="card card-hover overflow-hidden">
                    {/* League Header */}
                    <div className={cn("bg-gradient-to-r p-6 text-white", league.gradient)}>
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-2xl font-bold">{league.name}</h3>
                          <p className="text-sm text-white/80">{league.fullName}</p>
                        </div>
                        <league.icon className="w-10 h-10 opacity-80" />
                      </div>
                    </div>

                    {/* League Body */}
                    <div className="p-6">
                      <p className="text-text-muted text-sm mb-4 leading-relaxed">
                        {league.description}
                      </p>

                      <div className="flex items-center justify-between">
                        <div className={cn("text-sm font-semibold", league.accentColor)}>
                          {league.gamesCount} games today
                        </div>
                        <div className="flex items-center gap-1 text-sm font-semibold text-text-dark group-hover:text-primary transition-colors">
                          Enter
                          <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-white border-t border-border">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {PLATFORM_FEATURES.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
                className="text-center"
              >
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-primary/10 mb-4">
                  <feature.icon className="w-7 h-7 text-primary" />
                </div>
                <h3 className="text-xl font-bold text-text-dark mb-2">{feature.title}</h3>
                <p className="text-text-muted">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-navy py-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
                <svg viewBox="0 0 40 40" className="w-8 h-8">
                  <circle cx="20" cy="20" r="16" fill="#E85D04" />
                  <path d="M 4 20 Q 20 15, 36 20" stroke="#1A202C" strokeWidth="1.5" fill="none" />
                  <path d="M 4 20 Q 20 25, 36 20" stroke="#1A202C" strokeWidth="1.5" fill="none" />
                  <line x1="20" y1="4" x2="20" y2="36" stroke="#1A202C" strokeWidth="1.5" />
                </svg>
              </div>
              <span className="text-xl font-extrabold text-white text-display">
                blow<span className="text-primary">rout</span>
              </span>
            </div>

            <div className="text-white/60 text-sm text-center md:text-right">
              <p>© 2026 blowrout. All rights reserved.</p>
              <p className="text-xs mt-1">Advance Basketball Prediction Platform</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
