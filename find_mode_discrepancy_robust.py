import os
import requests
from dotenv import load_dotenv
from utils.ssl_adapter import get_robust_session

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

def find_discrepancy_robust():
    # Construct direct Postgrest URL
    url = f"{SUPABASE_URL}/rest/v1/predictions_history"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Range": "0-999" # Limit to 1000
    }
    params = {
        "league": "ilike.ncaa",
        "status": "eq.graded",
        "select": "*"
    }
    
    session = get_robust_session(retries=3)
    
    print("Fetching NCAA graded records (Robust)...")
    resp = session.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    safe_games = {} 
    full_games = {}
    
    for row in data:
        key = (row['game_date'], row['matchup'].lower().strip())
        if row['mode'] == 'safe':
            safe_games[key] = row
        elif row['mode'] == 'full':
            full_games[key] = row
            
    print(f"Total Graded NCAA SAFE: {len(safe_games)}")
    print(f"Total Graded NCAA FULL: {len(full_games)}")
    
    missing_in_full = []
    for key in safe_games:
        if key not in full_games:
            missing_in_full.append(key)
            
    if missing_in_full:
        print("\n--- Games in SAFE but MISSING in FULL ---")
        # Format for copy-pasting into a backfill list
        dates = sorted(list(set(d for d, m in missing_in_full)))
        for d in dates:
            print(f"\nDate: {d}")
            for date, matchup in sorted(missing_in_full):
                if date == d:
                    print(f"  - {matchup}")
    else:
        print("\nNo games missing in FULL.")

if __name__ == "__main__":
    find_discrepancy_robust()
