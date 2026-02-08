import asyncio
import os
import json
import sys
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import zoneinfo

# Add root for core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.basketball_engine import UniversalBasketballEngine
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ET_TZ = zoneinfo.ZoneInfo("America/New_York")

# Config path for NCAA
NCAA_CONFIG_SAFE = "configs/leagues/ncaa.json"

# Local stats files
BARTTORVIK_FILE = "data/barttorvik_stats.json"

def load_json(path):
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def sync_all_modes():
    bt = load_json(BARTTORVIK_FILE)
    safe_engine = UniversalBasketballEngine(NCAA_CONFIG_SAFE, mode="safe")
    full_engine = UniversalBasketballEngine(NCAA_CONFIG_SAFE, mode="full")
    
    # Check last 7 days
    for i in range(7):
        date_obj = datetime.now(ET_TZ) - timedelta(days=i)
        date_str = date_obj.strftime("%Y-%m-%d")
        print(f"\nChecking {date_str}...")
        
        res = supabase.table("predictions_history").select("*").ilike("league", "ncaa").eq("game_date", date_str).execute()
        data = res.data
        
        matchups = {} # matchup -> {mode: row}
        for row in data:
            m = row['matchup'].lower().strip()
            if m not in matchups: matchups[m] = {}
            matchups[m][row['mode']] = row
            
        new_rows = []
        for m_name, modes in matchups.items():
            if 'safe' in modes and 'full' not in modes:
                print(f"  Missing FULL for: {m_name}")
                # Create FULL from SAFE
                r = modes['safe']
                parts = r['matchup'].split(" @ ")
                teamA = find_team_in_dict(parts[0], bt, BASKETBALL_ALIASES)
                teamH = find_team_in_dict(parts[1], bt, BASKETBALL_ALIASES)
                if teamA and teamH:
                    sA, sH = bt[teamA], bt[teamH]
                    game_data = {
                        "team": teamA, "opponent": teamH, "market_total": r['market_total'],
                        "pace_adjustment": (sA.get('adj_t', 70.0) + sH.get('adj_t', 70.0)) / 2,
                        "efficiency_adjustment": (sA.get('adj_off', 110.0) + sH.get('adj_def', 110.0) + sH.get('adj_off', 110.0) + sA.get('adj_def', 110.0)) / 4,
                        "statsA": sA, "statsH": sH
                    }
                    res_eng = full_engine.calculate_total(game_data)
                    row_id = f"ncaa_{date_str}_{teamA}_{teamH}_full".replace(" ", "_").lower()
                    new_rows.append({
                        "id": row_id, "league": "ncaa", "game_date": date_str, "matchup": r['matchup'],
                        "market_total": float(r['market_total']), "model_total": float(res_eng['final_model_total']),
                        "edge": float(res_eng['edge']), "status": "pending", "mode": "full", "updated_at": datetime.now().isoformat()
                    })
            elif 'full' in modes and 'safe' not in modes:
                print(f"  Missing SAFE for: {m_name}")
                # Create SAFE from FULL
                r = modes['full']
                parts = r['matchup'].split(" @ ")
                teamA = find_team_in_dict(parts[0], bt, BASKETBALL_ALIASES)
                teamH = find_team_in_dict(parts[1], bt, BASKETBALL_ALIASES)
                if teamA and teamH:
                    sA, sH = bt[teamA], bt[teamH]
                    game_data = {
                        "team": teamA, "opponent": teamH, "market_total": r['market_total'],
                        "pace_adjustment": (sA.get('adj_t', 70.0) + sH.get('adj_t', 70.0)) / 2,
                        "efficiency_adjustment": (sA.get('adj_off', 110.0) + sH.get('adj_def', 110.0) + sH.get('adj_off', 110.0) + sA.get('adj_def', 110.0)) / 4,
                        "statsA": sA, "statsH": sH
                    }
                    res_eng = safe_engine.calculate_total(game_data)
                    row_id = f"ncaa_{date_str}_{teamA}_{teamH}_safe".replace(" ", "_").lower()
                    new_rows.append({
                        "id": row_id, "league": "ncaa", "game_date": date_str, "matchup": r['matchup'],
                        "market_total": float(r['market_total']), "model_total": float(res_eng['final_model_total']),
                        "edge": float(res_eng['edge']), "status": "pending", "mode": "safe", "updated_at": datetime.now().isoformat()
                    })
                    
        if new_rows:
            print(f"  Pushing {len(new_rows)} missing records...")
            supabase.table("predictions_history").upsert(new_rows, on_conflict="id").execute()
            print("  Done.")

if __name__ == "__main__":
    sync_all_modes()
