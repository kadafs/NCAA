import os
import json
import sys
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Add root for core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.basketball_engine import UniversalBasketballEngine
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Config path for NCAA
NCAA_CONFIG = "configs/leagues/ncaa.json"

# Local stats files
BARTTORVIK_FILE = "data/barttorvik_stats.json"
CONSOLIDATED_FILE = "data/consolidated_stats.json"

def load_json(path):
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_ppg(team_name, stats, bt_data):
    # Same logic as ncaa/v1_2/populate.py
    for entry in stats.get('scoring_offense', []):
        if entry['Team'] == team_name:
            return float(entry['PPG'])
    # Fallback to engine-derived
    s = bt_data.get(team_name, {})
    return (s.get('adj_off', 110) * (s.get('adj_t', 70) / 100))

def sync_from_safe(date_str):
    print(f"Syncing FULL records from SAFE records for {date_str}...")
    
    # 1. Fetch SAFE records
    res = supabase.table("predictions_history").select("*").ilike("league", "ncaa").eq("game_date", date_str).eq("mode", "safe").execute()
    safe_rows = res.data
    
    # 2. Fetch FULL records to check what's missing
    res_full = supabase.table("predictions_history").select("*").ilike("league", "ncaa").eq("game_date", date_str).eq("mode", "full").execute()
    full_matchups = {r['matchup'].lower().strip() for r in res_full.data}
    
    missing = [r for r in safe_rows if r['matchup'].lower().strip() not in full_matchups]
    print(f"Found {len(missing)} missing FULL records.")
    
    if not missing:
        return
    
    # 3. Load Engine & Stats
    engine = UniversalBasketballEngine(NCAA_CONFIG, mode="full")
    bt = load_json(BARTTORVIK_FILE)
    sh = load_json(CONSOLIDATED_FILE)
    
    new_rows = []
    for r in missing:
        matchup = r['matchup']
        parts = matchup.split(" @ ")
        away_name, home_name = parts[0], parts[1]
        
        # Resolve names
        teamA = find_team_in_dict(away_name, bt, BASKETBALL_ALIASES)
        teamH = find_team_in_dict(home_name, bt, BASKETBALL_ALIASES)
        
        if not teamA or not teamH:
            print(f" Could not resolve teams for {matchup}")
            continue
            
        sA = bt[teamA]
        sH = bt[teamH]
        
        # Prepare game_data for engine
        # Match pop_ncaa logic in data_bridge.py
        game_data = {
            "team": teamA,
            "opponent": teamH,
            "market_total": r['market_total'],
            "pace_adjustment": (sA.get('adj_t', 70.0) + sH.get('adj_t', 70.0)) / 2,
            "efficiency_adjustment": (sA.get('adj_off', 110.0) + sH.get('adj_def', 110.0) + sH.get('adj_off', 110.0) + sA.get('adj_def', 110.0)) / 4,
            "projected_spread": 10.0, # Default for sync
            "statsA": sA,
            "statsH": sH
        }
        
        res = engine.calculate_total(game_data)
        
        # 4. Prepare FULL row
        row_id = f"ncaa_{date_str}_{teamA}_{teamH}_full".replace(" ", "_").lower()
        new_rows.append({
            "id": row_id,
            "league": "ncaa",
            "game_date": date_str,
            "matchup": matchup,
            "market_total": float(r['market_total']),
            "model_total": float(res['final_model_total']),
            "edge": float(res['edge']),
            "status": "pending",
            "mode": "full",
            "updated_at": datetime.now().isoformat()
        })
        
    if new_rows:
        print(f"Pushing {len(new_rows)} FULL records...")
        supabase.table("predictions_history").upsert(new_rows, on_conflict="id").execute()
        print("Push complete.")

if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "2026-02-05"
    sync_from_safe(d)
