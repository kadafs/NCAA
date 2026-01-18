import json
import os
import zoneinfo
from datetime import datetime
import sys

# Add root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

# Data Paths
STATS_FILE = "data/nba_stats.json"
MATCHUP_FILE = "data/nba_matchups.json"

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r") as f: return json.load(f)

def predict_game(away_name, home_name, stats_dict):
    # Find match using shared utility
    teamA = find_team_in_dict(away_name, stats_dict, BASKETBALL_ALIASES)
    teamH = find_team_in_dict(home_name, stats_dict, BASKETBALL_ALIASES)
    
    if not teamA or not teamH:
        return None
        
    sA, sH = stats_dict[teamA], stats_dict[teamH]
    
    # Pace is per 48 mins
    avg_pace = (sA['adj_t'] + sH['adj_t']) / 2
    
    # Points per 100 possessions
    # (OffA + DefH) / 2
    effA = (sA['adj_off'] + sH['adj_def']) / 2
    effH = (sH['adj_off'] + sA['adj_def']) / 2
    
    projA = (avg_pace / 100) * effA
    projH = (avg_pace / 100) * effH
    
    # Home court advantage in NBA (~2.5 points)
    projH += 2.5
    
    return {
        "scoreA": round(projA, 1),
        "scoreH": round(projH, 1),
        "total": round(projA + projH, 1),
        "spread": round(projH - projA, 1),
        "metricsA": sA,
        "metricsH": sH
    }

def main():
    stats = load_json(STATS_FILE)
    if not stats:
        print(f"Error: {STATS_FILE} missing. Run nba/fetch_nba_stats.py first.")
        return
        
    matchups = load_json(MATCHUP_FILE)
    if not matchups:
        # Fallback to fetching it now if missing
        from nba.fetch_nba_schedule import fetch_nba_daily_schedule
        matchups = fetch_nba_daily_schedule()
        
    if not matchups:
        print("No NBA games scheduled for today.")
        return

    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n--- NBA Predictions for {now.strftime('%Y-%m-%d')} ---")
    
    header = f"{'Matchup':<35} | {'Proj Score':<15} | {'Spread':<8} | {'Pace':<6} | {'eFG% (A/H)':<12} | {'OR% (A/H)':<12}"
    print(header)
    print("-" * len(header))
    
    for m in matchups:
        res = predict_game(m['away'], m['home'], stats)
        if res:
            match_str = f"{m['away']} @ {m['home']}"
            score_str = f"{res['scoreA']} - {res['scoreH']}"
            spread_str = f"{res['spread']:+.1f}"
            pace_str = f"{res['metricsA']['adj_t']:.1f}" # Just showing away pace for now
            efg_str = f"{res['metricsA']['efg']:.1f}/{res['metricsH']['efg']:.1f}"
            or_str = f"{res['metricsA']['or']:.1f}/{res['metricsH']['or']:.1f}"
            
            print(f"{match_str:<35} | {score_str:<15} | {spread_str:<8} | {pace_str:<6} | {efg_str:<12} | {or_str:<12}")

if __name__ == "__main__":
    main()
