import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_lines(date_str):
    print(f"Verifying market lines for {date_str}...")
    res = supabase.table("predictions_history").select("id, matchup, market_total, status").ilike("league", "ncaa").eq("game_date", date_str).execute()
    data = res.data
    
    defaults = [r for r in data if r['market_total'] == 145.5]
    diffs = [r for r in data if r['market_total'] != 145.5]
    
    print(f"Total Records: {len(data)}")
    print(f"Records with 145.5: {len(defaults)}")
    print(f"Records with OTHER: {len(diffs)}")
    
    if diffs:
        print(f"Sample OTHER: {diffs[0]['matchup']} -> {diffs[0]['market_total']} ({diffs[0]['status']})")

if __name__ == "__main__":
    verify_lines("2026-02-07")
