import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_remaining(date_str):
    print(f"Listing 145.5 games for {date_str}...")
    res = supabase.table("predictions_history").select("id, matchup, market_total, status").ilike("league", "ncaa").eq("game_date", date_str).eq("market_total", 145.5).execute()
    data = res.data
    
    for r in data:
        print(f"  '{r['matchup']}'")

if __name__ == "__main__":
    list_remaining("2026-02-07")
