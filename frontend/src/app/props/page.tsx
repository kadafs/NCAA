"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
    Search,
    Filter,
    Zap,
    TrendingUp,
    ArrowUpRight,
    ChevronDown,
    Flame
} from "lucide-react";
import { cn } from "@/lib/utils";
import { LeftSidebar, BottomNav } from "@/components/dashboard/LeftSidebar";
import { PropCard } from "@/components/dashboard/PropCard";
import { PlayerProp } from "@/types";

/**
 * Props Page - High-Edge Player Props Board
 * 
 * Features:
 * - Search and filter functionality
 * - Grid of player prop cards
 * - High-edge props highlighted
 * - Mobile-first responsive design
 */

const MOCK_PROPS: PlayerProp[] = [
    {
        id: "p1",
        name: "LeBron James",
        team: "Lakers",
        teamCode: "LAL",
        position: "Forward",
        image: "https://a.espncdn.com/i/headshots/nba/players/full/1966.png",
        propType: "PTS",
        line: 24.5,
        projection: 28.2,
        edge: 3.7,
        edgePct: 15.1,
        usageBoost: true,
        recentTrend: [1, 1, -1, 1, 1]
    },
    {
        id: "p2",
        name: "Jayson Tatum",
        team: "Celtics",
        teamCode: "BOS",
        position: "Forward",
        image: "https://a.espncdn.com/i/headshots/nba/players/full/4065648.png",
        propType: "PTS",
        line: 27.5,
        projection: 29.8,
        edge: 2.3,
        edgePct: 8.4,
        usageBoost: false,
        recentTrend: [1, -1, 1, 1, 1]
    },
    {
        id: "p3",
        name: "Luka Doncic",
        team: "Mavericks",
        teamCode: "DAL",
        position: "Guard",
        image: "https://a.espncdn.com/i/headshots/nba/players/full/3945274.png",
        propType: "AST",
        line: 8.5,
        projection: 10.2,
        edge: 1.7,
        edgePct: 20.0,
        usageBoost: true,
        recentTrend: [1, 1, 1, 1, -1]
    },
    {
        id: "p4",
        name: "Nikola Jokic",
        team: "Nuggets",
        teamCode: "DEN",
        position: "Center",
        image: "https://a.espncdn.com/i/headshots/nba/players/full/3112335.png",
        propType: "REB",
        line: 12.5,
        projection: 14.1,
        edge: 1.6,
        edgePct: 12.8,
        usageBoost: false,
        recentTrend: [1, 1, 1, -1, 1]
    },
    {
        id: "p5",
        name: "Shai Gilgeous-Alexander",
        team: "Thunder",
        teamCode: "OKC",
        position: "Guard",
        image: "https://a.espncdn.com/i/headshots/nba/players/full/4278073.png",
        propType: "PTS",
        line: 30.5,
        projection: 33.8,
        edge: 3.3,
        edgePct: 10.8,
        usageBoost: true,
        recentTrend: [1, 1, 1, 1, 1]
    },
    {
        id: "p6",
        name: "Anthony Edwards",
        team: "Timberwolves",
        teamCode: "MIN",
        position: "Guard",
        image: "https://a.espncdn.com/i/headshots/nba/players/full/4594327.png",
        propType: "PTS",
        line: 25.5,
        projection: 27.9,
        edge: 2.4,
        edgePct: 9.4,
        usageBoost: false,
        recentTrend: [-1, 1, 1, -1, 1]
    },
];

const PROP_TYPES = ["All", "PTS", "REB", "AST", "P+R+A"];
const LEAGUES = ["All", "NBA", "NCAA"];

export default function PropsPage() {
    const [activeTab, setActiveTab] = useState("props");
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedPropType, setSelectedPropType] = useState("All");
    const [selectedLeague, setSelectedLeague] = useState("All");
    const [sortBy, setSortBy] = useState<"edge" | "edgePct">("edgePct");
    const [props, setProps] = useState<PlayerProp[]>([]);
    const [loading, setLoading] = useState(true);

    React.useEffect(() => {
        fetchProps();
    }, [selectedLeague]);

    const fetchProps = async () => {
        setLoading(true);
        try {
            // Fetch NBA by default since NCAA props might be limited
            const leagueQuery = selectedLeague === "All" ? "nba" : selectedLeague.toLowerCase();
            const res = await fetch(`/api/predictions?league=${leagueQuery}`);
            const data = await res.json();

            if (data.games) {
                const allProps: PlayerProp[] = [];

                data.games.forEach((game: any) => {
                    if (game.props && game.props.length > 0) {
                        game.props.forEach((p: any) => {
                            // Map incoming API prop to our frontend type
                            // Temporary: logic to make the 'line' look realistic
                            const baseline = p.pts > 25 ? Math.floor(p.pts - 1.5) + 0.5 : Math.floor(p.pts - 0.5) + 0.5;
                            const edge = p.pts - baseline;
                            const edgePct = (edge / baseline) * 100;

                            allProps.push({
                                id: p.id || `${game.matchup}-${p.name}`,
                                name: p.name,
                                team: p.team_label === 'A' ? game.away : game.home,
                                teamCode: p.team_label === 'A' ? game.away_details?.code : game.home_details?.code,
                                position: "G/F",
                                image: p.id ? `https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/${p.id}.png` : "",
                                propType: "PTS",
                                line: baseline,
                                projection: p.pts,
                                edge: edge,
                                edgePct: edgePct,
                                usageBoost: p.trace?.some((t: string) => t.includes('usage')),
                                recentTrend: [1, 1, 1]
                            });
                        });
                    }
                });

                setProps(allProps);
            } else {
                setProps(MOCK_PROPS);
            }
        } catch (err) {
            console.error("Props fetch error:", err);
            setProps(MOCK_PROPS);
        } finally {
            setLoading(false);
        }
    };

    // Filter and sort props
    const filteredProps = props
        .filter(prop => {
            if (searchQuery && !prop.name.toLowerCase().includes(searchQuery.toLowerCase())) {
                return false;
            }
            if (selectedPropType !== "All" && prop.propType !== selectedPropType) {
                return false;
            }
            return true;
        })
        .sort((a, b) => sortBy === "edge" ? b.edge - a.edge : b.edgePct - a.edgePct);

    return (
        <div className="min-h-screen bg-dash-bg text-dash-text-primary">
            {/* Left Sidebar - Desktop */}
            <LeftSidebar />

            {/* Main Content */}
            <div className="lg:ml-16 xl:ml-20">
                {/* Header */}
                <header className="sticky top-0 z-30 bg-dash-bg/80 backdrop-blur-xl border-b border-dash-border">
                    <div className="px-4 py-4 md:px-6 lg:px-8">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div>
                                <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tighter flex items-center gap-3">
                                    <Flame className="w-7 h-7 text-gold" />
                                    Player <span className="text-gold italic">Props</span>
                                </h1>
                                <p className="text-[10px] md:text-xs font-bold text-dash-text-muted uppercase tracking-widest mt-1">
                                    High-Edge Prop Predictions • {filteredProps.length} Active
                                </p>
                            </div>

                            {/* Search */}
                            <div className="relative max-w-sm w-full">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dash-text-muted" />
                                <input
                                    type="text"
                                    placeholder="Search players..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full bg-dash-bg-secondary border border-dash-border rounded-xl py-2.5 pl-10 pr-4 text-xs font-medium text-white placeholder:text-dash-text-muted focus:outline-none focus:border-gold/50 transition-colors"
                                />
                            </div>
                        </div>

                        {/* Filters */}
                        <div className="flex flex-wrap items-center gap-3 mt-4">
                            {/* Prop Type Filter */}
                            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
                                {PROP_TYPES.map((type) => (
                                    <button
                                        key={type}
                                        onClick={() => setSelectedPropType(type)}
                                        className={cn(
                                            "px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all whitespace-nowrap",
                                            selectedPropType === type
                                                ? "bg-gold text-dash-bg"
                                                : "bg-dash-bg-secondary border border-dash-border text-dash-text-muted hover:text-white"
                                        )}
                                    >
                                        {type}
                                    </button>
                                ))}
                            </div>

                            <div className="h-6 w-px bg-dash-border hidden md:block" />

                            {/* League Filter */}
                            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
                                {LEAGUES.map((league) => (
                                    <button
                                        key={league}
                                        onClick={() => setSelectedLeague(league)}
                                        className={cn(
                                            "px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all whitespace-nowrap",
                                            selectedLeague === league
                                                ? "bg-cyan text-dash-bg"
                                                : "bg-dash-bg-secondary border border-dash-border text-dash-text-muted hover:text-white"
                                        )}
                                    >
                                        {league}
                                    </button>
                                ))}
                            </div>

                            <div className="ml-auto">
                                <button
                                    onClick={() => setSortBy(sortBy === "edge" ? "edgePct" : "edge")}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-dash-bg-secondary border border-dash-border rounded-lg text-[10px] font-bold text-dash-text-muted uppercase hover:text-white transition-colors"
                                >
                                    <TrendingUp className="w-3 h-3" />
                                    Sort: {sortBy === "edge" ? "Edge" : "Edge %"}
                                    <ChevronDown className="w-3 h-3" />
                                </button>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Props Grid */}
                <main className="p-4 md:p-6 lg:p-8 pb-24 lg:pb-8">
                    <div className="max-w-[1600px] mx-auto">
                        {loading ? (
                            <div className="bg-dash-card border border-dash-border rounded-3xl p-12 flex flex-col items-center justify-center gap-4">
                                <div className="w-8 h-8 border-2 border-gold border-t-transparent rounded-full animate-spin" />
                                <p className="text-sm font-bold text-dash-text-muted">Analyzing market props...</p>
                            </div>
                        ) : (
                            <>
                                {/* High Edge Alert */}
                                {filteredProps.filter(p => p.edgePct > 10).length > 0 && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="mb-6 p-4 bg-gold/10 border border-gold/20 rounded-2xl flex items-center gap-4"
                                    >
                                        <div className="w-10 h-10 bg-gold rounded-xl flex items-center justify-center flex-shrink-0">
                                            <Zap className="w-5 h-5 text-dash-bg" />
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-bold text-gold uppercase">High Edge Alert</h3>
                                            <p className="text-xs text-dash-text-muted mt-0.5">
                                                {filteredProps.filter(p => p.edgePct > 10).length} props with 10%+ edge detected today
                                            </p>
                                        </div>
                                    </motion.div>
                                )}

                                {/* Grid */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                    {filteredProps.map((prop, idx) => (
                                        <motion.div
                                            key={prop.id}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                        >
                                            <PropCard prop={prop} />
                                        </motion.div>
                                    ))}
                                </div>

                                {filteredProps.length === 0 && (
                                    <div className="text-center py-20">
                                        <p className="text-dash-text-muted">No props matching your filters.</p>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </main>
            </div>

            {/* Bottom Nav - Mobile */}
            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
    );
}
