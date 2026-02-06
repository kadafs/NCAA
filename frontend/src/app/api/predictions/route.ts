import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const dynamic = 'force-dynamic';

/**
 * Predictions API Route (Vercel/Production optimized)
 * 
 * Fetches pre-generated predictions from Supabase 'predictions_store' table.
 * Data is updated on a schedule via GitHub Actions.
 */

export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const league = searchParams.get("league") || "nba";
        const mode = searchParams.get("mode") || "safe";

        // Fetch from Supabase store using composite key
        const storeKey = `${league}_${mode}`;
        const { data: storeData, error } = await supabase
            .from("predictions_store")
            .select("data, updated_at")
            .eq("league", storeKey)
            .single();

        if (error || !storeData) {
            console.error("Supabase Read Error:", error);

            // Fallback for development/demo mode if Supabase is failing or unconfigured
            const mockData: Record<string, any> = {
                nba: {
                    games: [
                        {
                            time: "LIVE",
                            date: "TODAY",
                            away: { name: "Lakers", code: "LAL", score: 102 },
                            home: { name: "Celtics", code: "BOS", score: 108 },
                            market_total: 234.5,
                            model_total: 238.2,
                            edge: 3.7,
                            confidence: "strong"
                        }
                    ],
                    audit: { last_48h: { wins: 24, losses: 11, pct: 84.2 } }
                },
                ncaa: {
                    games: [
                        {
                            time: "7:00 PM",
                            date: "TODAY",
                            away: { name: "Duke", code: "DUKE" },
                            home: { name: "UNC", code: "UNC" },
                            market_total: 145.5,
                            model_total: 148.7,
                            edge: 3.2,
                            confidence: "strong"
                        }
                    ],
                    audit: { last_48h: { wins: 42, losses: 18, pct: 70.0 } }
                }
            };

            const fallback = mockData[league] || mockData.nba;
            return NextResponse.json({
                ...fallback,
                isMock: true,
                warning: "Using mock data due to Supabase connection failure."
            });
        }

        const predictions = storeData.data;

        // 1. Fetch real audit data for this league
        let audit = null;
        try {
            const { data: summary } = await supabase
                .from("audit_summary")
                .select("*")
                .eq("league", league.toLowerCase())
                .single();

            if (summary) {
                audit = {
                    last_48h: {
                        pct: summary.win_pct || 0,
                        wins: summary.wins || 0,
                        losses: summary.losses || 0,
                        pushes: summary.pushes || 0
                    }
                };
            }
        } catch (e) {
            console.warn("Could not fetch audit summary for league:", league);
        }

        return NextResponse.json({
            ...predictions,
            audit,
            lastUpdated: storeData.updated_at
        }, {
            headers: {
                'Cache-Control': 's-maxage=60, stale-while-revalidate=30'
            }
        });

    } catch (error) {
        console.error("API Route Error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
