import os
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
import sys

# Add parent dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.audit_engine import fetch_ncaa_scores_espn, get_canonical_key, grade_total
from utils.mapping import clean_team_name

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def force_grade_ncaa_full():
    date_str = "2026-02-04"
    print(f"--- Force Grading NCAA FULL for {date_str} ---")
    
    # 1. Fetch pending
    res = supabase.table("predictions_history") \
        .select("*") \
        .ilike("league", "ncaa") \
        .eq("mode", "full") \
        .eq("game_date", date_str) \
        .eq("status", "pending") \
        .execute()
    
    pending = res.data
    print(f"Found {len(pending)} pending rows.")
    
    if not pending: return

    # 2. Fetch results
    results_map = fetch_ncaa_scores_espn(date_str)
    print(f"Fetched {len(results_map)} results from ESPN.")

    updates = []
    for row in pending:
        parts = [p.strip() for p in row['matchup'].split('@')]
        if len(parts) != 2: continue
        
        db_key = get_canonical_key(parts[0], parts[1])
        matched_key = None
        
        # Try direct match
        if db_key in results_map:
            matched_key = db_key
        else:
            # Try fuzzy match
            for r_key in results_map:
                ra, rh = r_key.split('_')
                da, dh = db_key.split('_')
                if (da in ra or ra in da) and (dh in rh or rh in dh):
                    matched_key = r_key
                    break
        
        if matched_key:
            res = results_map[matched_key]
            market_total = row['market_total']
            model_total = row['model_total']
            direction = "OVER" if model_total > market_total else "UNDER"
            actual_direction = grade_total(market_total, res['away_score'], res['home_score'])
            
            is_win = None if actual_direction == "PUSH" else (direction == actual_direction)
            
            updates.append({
                "id": row['id'],
                "actual_score_away": res['away_score'],
                "actual_score_home": res['home_score'],
                "actual_total": res['total'],
                "is_win": is_win,
                "status": "graded",
                "profit": 0.91 if is_win else -1.0 if is_win is False else 0.0,
                "updated_at": datetime.now().isoformat()
            })
            print(f"  [WINNER] Matched: {row['matchup']} -> {matched_key}")
        else:
            print(f"  [FAILED] No match for: {row['matchup']} (Key: {db_key})")

    if updates:
        print(f"Pushing {len(updates)} updates...")
        supabase.table("predictions_history").upsert(updates).execute()
        print("Done.")
    else:
        print("No updates to push.")

if __name__ == "__main__":
    force_grade_ncaa_full()
