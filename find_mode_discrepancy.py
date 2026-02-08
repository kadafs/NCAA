import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def find_discrepancy():
    print("Fetching NCAA graded records...")
    
    # Fetch all NCAA graded records
    # We'll fetch in batches if needed, but 1000 should cover it for now
    res = supabase.table("predictions_history").select("*").ilike("league", "ncaa").eq("status", "graded").limit(1000).execute()
    data = res.data
    
    safe_games = {} # (date, matchup) -> row
    full_games = {} # (date, matchup) -> row
    
    for row in data:
        key = (row['game_date'], row['matchup'].lower().strip())
        if row['mode'] == 'safe':
            safe_games[key] = row
        elif row['mode'] == 'full':
            full_games[key] = row
            
    print(f"Total Graded NCAA SAFE: {len(safe_games)}")
    print(f"Total Graded NCAA FULL: {len(full_games)}")
    
    # Find SAFE games missing in FULL
    missing_in_full = []
    for key in safe_games:
        if key not in full_games:
            missing_in_full.append(key)
            
    # Find FULL games missing in SAFE
    missing_in_safe = []
    for key in full_games:
        if key not in safe_games:
            missing_in_safe.append(key)
            
    if missing_in_full:
        print("\n--- Games in SAFE but MISSING in FULL ---")
        for date, matchup in sorted(missing_in_full):
            print(f" {date}: {matchup}")
    else:
        print("\nNo games missing in FULL.")
        
    if missing_in_safe:
        print("\n--- Games in FULL but MISSING in SAFE ---")
        for date, matchup in sorted(missing_in_safe):
            print(f" {date}: {matchup}")
    else:
        print("\nNo games missing in SAFE.")

if __name__ == "__main__":
    find_discrepancy()
