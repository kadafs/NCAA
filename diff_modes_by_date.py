import os
import argparse
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def diff_date(date_str):
    print(f"Comparing NCAA modes for {date_str}...")
    res = supabase.table("predictions_history").select("*").ilike("league", "ncaa").eq("game_date", date_str).execute()
    data = res.data
    
    safe = set()
    full = set()
    
    for row in data:
        if row['mode'] == 'safe':
            safe.add(row['matchup'].lower().strip())
        elif row['mode'] == 'full':
            full.add(row['matchup'].lower().strip())
            
    only_safe = safe - full
    only_full = full - safe
    
    print(f"SAFE games: {len(safe)}")
    print(f"FULL games: {len(full)}")
    
    if only_safe:
        print("\nOnly in SAFE:")
        for m in sorted(only_safe):
            print(f" - {m}")
            
    if only_full:
        print("\nOnly in FULL:")
        for m in sorted(only_full):
            print(f" - {m}")

if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "2026-02-07"
    diff_date(d)
