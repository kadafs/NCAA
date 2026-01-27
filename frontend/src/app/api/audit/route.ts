import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

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

        // 2. Fetch Recent Graded Picks
        const { data: recentPicks, error: picksError } = await supabase
            .from("predictions_history")
            .select("*")
            .eq("status", "graded")
            .order("game_date", { ascending: false })
            .limit(10);

        if (picksError) throw picksError;

        return NextResponse.json({
            metrics: summaryData || [],
            recent: recentPicks || [],
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error("Audit API Error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
