
import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const dynamic = 'force-dynamic';

/**
 * Audit API Route
 * 
 * Fetches real performance metrics from Supabase 'audit_summary' and 'predictions_history' tables.
 */

export async function GET(req: Request) {
    try {
        // 1. Fetch Summary Data
        const { data: summaryData, error: summaryError } = await supabase
            .from("audit_summary")
            .select("*");

        if (summaryError) throw summaryError;

        // 2. Fetch Recent Graded Picks (200 per category)
        const categories = [
            { league: 'nba', mode: 'safe' },
            { league: 'nba', mode: 'full' },
            { league: 'ncaa', mode: 'safe' },
            { league: 'ncaa', mode: 'full' }
        ];

        const picksPromises = categories.map(cat =>
            supabase
                .from("predictions_history")
                .select("*")
                .eq("status", "graded")
                .ilike("league", cat.league)
                .eq("mode", cat.mode)
                .order("game_date", { ascending: false })
                .limit(200)
        );

        const results = await Promise.all(picksPromises);

        // Check for errors in any of the parallel requests
        for (const res of results) {
            if (res.error) throw res.error;
        }

        const recentPicks = results.flatMap(res => res.data || []);

        return NextResponse.json({
            metrics: summaryData || [],
            recent: recentPicks || [],
            timestamp: new Date().toISOString()
        }, {
            headers: {
                'Cache-Control': 's-maxage=60, stale-while-revalidate=30'
            }
        });

    } catch (error) {
        console.error("Audit API Error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
