import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def debug_nba():
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("Missing URL or Key")
        return

    supabase = create_client(url, key)
    
    print("Checking predictions_history for NBA on 2026-02-15...")
    
    # Check for any status
    res = supabase.table("predictions_history") \
        .select("*") \
        .ilike("league", "nba") \
        .eq("game_date", "2026-02-15") \
        .execute()
        
    print(f"Found {len(res.data)} records.")
    for row in res.data:
        print(f"Matchup: {row.get('matchup')}, Status: {row.get('status')}, League: {row.get('league')}, Mode: {row.get('mode')}")

if __name__ == "__main__":
    debug_nba()
