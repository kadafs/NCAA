import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def final_fix_v2():
    # 1. Fix USC -> Texas A&M-CC
    print("Fixing USC -> Texas A&M-CC...")
    res = supabase.table("predictions_history").select("*").eq("game_date", "2026-02-07").ilike("matchup", "%USC @ Nicholls%").execute()
    for r in res.data:
        new_matchup = "Texas A&M-CC @ Nicholls St."
        total = 137.5
        model_total = r['model_total']
        new_edge = round(model_total - total, 2)
        
        supabase.table("predictions_history").update({
            "matchup": new_matchup,
            "market_total": total,
            "edge": new_edge,
            "status": "pending",
            "updated_at": datetime.now().isoformat()
        }).eq("id", r['id']).execute()
        print(f"  Updated {r['matchup']} -> {new_matchup} (137.5)")

    # 2. Fix Alcorn St.
    print("Fixing Alcorn St. -> 144.5...")
    res = supabase.table("predictions_history").select("*").eq("game_date", "2026-02-07").ilike("matchup", "%Alcorn%").execute()
    for r in res.data:
        total = 144.5
        model_total = r['model_total']
        new_edge = round(model_total - total, 2)
        
        supabase.table("predictions_history").update({
            "market_total": total,
            "edge": new_edge,
            "status": "pending",
            "updated_at": datetime.now().isoformat()
        }).eq("id", r['id']).execute()
        print(f"  Updated {r['matchup']} -> 144.5")

if __name__ == "__main__":
    final_fix_v2()
