import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

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

        // Fetch from Supabase store
        const { data: storeData, error } = await supabase
            .from("predictions_store")
            .select("data, updated_at")
            .eq("league", league)
            .single();

        if (error || !storeData) {
            console.error("Supabase Read Error:", error);
            const isConfigured = !!process.env.NEXT_PUBLIC_SUPABASE_URL && !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
            return NextResponse.json({
                error: error?.message || "Predictions not found in database.",
                details: error || (isConfigured ? "Table 'predictions_store' might be empty." : "Supabase Environment variables are MISSING on Vercel."),
                league,
                timestamp: new Date().toISOString()
            }, { status: 404 });
        }

        const predictions = storeData.data;

        // Load audit data from Supabase settings or separate audit table (v2)
        // For now, we assume bridge output includes audit or we return just games

        return NextResponse.json({
            ...predictions,
            lastUpdated: storeData.updated_at
        });

    } catch (error) {
        console.error("API Route Error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
