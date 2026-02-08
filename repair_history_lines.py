import os
import json
import sys
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Add root for core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.ssl_adapter import get_robust_session
from utils.odds_provider import extract_total_for_matchup

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def repair_date(date_str):
    print(f"--- Repairing History Lines for {date_str} ---")
    
    # 1. Fetch Historical Odds from Render
    url = f"https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa?date={date_str}"
    
    odds_data = None
    import time
    for attempt in range(10):
        print(f"Fetching historical odds (Attempt {attempt+1}/10)...")
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            # Try both with and without verification to bypass Render SSL quirks
            resp = requests.get(url, timeout=30, verify=False)
            if resp.status_code == 200:
                odds_data = resp.json()
                print(f"Successfully fetched odds on attempt {attempt+1}")
                break
            else:
                print(f" Attempt {attempt+1} failed with status: {resp.status_code}")
        except Exception as e:
            print(f" Attempt {attempt+1} error: {e}")
        
        time.sleep(2 * (attempt + 1))

    if not odds_data:
        print("Final failure: Could not fetch odds data after 10 attempts.")
        return
    
    print(f"Found {len(odds_data)} odds entries.")

    # 2. Fetch Existing History Records
    print(f"Fetching history records for {date_str}...")
    res = supabase.table("predictions_history").select("*").ilike("league", "ncaa").eq("game_date", date_str).execute()
    history_records = res.data
    print(f"Found {len(history_records)} history records.")

    updates = []
    matched_count = 0
    
    for r in history_records:
        matchup = r['matchup']
        parts = matchup.split(" @ ")
        if len(parts) != 2:
            parts = matchup.split(" vs ")
            
        if len(parts) != 2: continue
        
        away, home = parts[0].strip(), parts[1].strip()
        
        # Use existing utility for matching
        correct_total = extract_total_for_matchup(odds_data, away, home)
        
        if correct_total and correct_total != r['market_total']:
            # Calculate new edge
            model_total = r['model_total']
            new_edge = round(model_total - correct_total, 2)
            
            updates.append({
                "id": r['id'],
                "league": r['league'],
                "game_date": r['game_date'],
                "matchup": r['matchup'],
                "mode": r['mode'],
                "market_total": float(correct_total),
                "edge": float(new_edge),
                "status": "pending", # Reset to pending for re-audit
                "updated_at": datetime.now().isoformat()
            })
            matched_count += 1
            if matched_count % 20 == 0:
                print(f" Matched {matched_count} games...")

    if updates:
        print(f"Pushing {len(updates)} updates to Supabase...")
        # Chunk updates for Supabase
        for i in range(0, len(updates), 50):
            chunk = updates[i:i+50]
            supabase.table("predictions_history").upsert(chunk, on_conflict="id").execute()
        print("Repair complete.")
    else:
        print("No updates needed or no matches found.")

if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "2026-02-07"
    repair_date(d)
