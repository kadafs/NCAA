import json
import os
import zoneinfo
from datetime import datetime
import sys

# Add root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

STATS_FILE = os.path.join(ROOT_DIR, "data", "eurocup_stats.json")
MATCHUPS_FILE = os.path.join(ROOT_DIR, "data", "eurocup_matchups.json")

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return None

def main():
    stats = load_json(STATS_FILE)
    matchups = load_json(MATCHUPS_FILE)
    
    if stats is None or matchups is None:
        print("Required EuroCup data files (stats/matchups) are missing.")
        return

    # Use ET for consistency
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n--- EuroCup Simple Predictions for {now.strftime('%Y-%m-%d')} ---")
    print("(Based on PPG and OPP PPG averages)\n")
    
    if not matchups:
        print("No EuroCup games found for today.")
        return

    # Standardized Header
    header = f"{'Matchup':<35} | {'Proj Score':<15} | {'Spread':<8} | {'Conf (A/H)':<10} | {'Adj T(A/H)':<11} | {'AdjOE(A/H)':<12} | {'AdjDE(A/H)':<12} | {'eFG% (A/H)':<12} | {'TO% (A/H)':<12} | {'OR% (A/H)':<12} | {'FTR (A/H)':<12}"
    print(header)
    print("-" * len(header))
    
    for m in matchups:
        away_raw = m['away']
        home_raw = m['home']
        
        nameA = find_team_in_dict(away_raw, stats, BASKETBALL_ALIASES)
        nameH = find_team_in_dict(home_raw, stats, BASKETBALL_ALIASES)
        
        if nameA and nameH:
            sA = stats[nameA]
            sH = stats[nameH]
            
            # Simple Math: Average of Team A Offense and Team B Defense
            pA = sA.get('pts', 0)
            oA = sA.get('allowed', {}).get('pts', 0)
            pH = sH.get('pts', 0)
            oH = sH.get('allowed', {}).get('pts', 0)
            
            scoreA = (pA + oH) / 2
            scoreH = (pH + oA) / 2
            
            match_str = f"{away_raw} @ {home_raw}"
            score_str = f"{scoreA:.1f} - {scoreH:.1f}"
            spread_str = f"{scoreH - scoreA:+.1f}"
            
            # Metadata Lookup Meta
            conf_str = "ECUP/ECUP"
            t_str = f"{round(sA.get('adj_t', 0), 1)}/{round(sH.get('adj_t', 0), 1)}"
            oe_str = f"{round(sA.get('adj_off', 0), 1)}/{round(sH.get('adj_off', 0), 1)}"
            de_str = f"{round(sA.get('adj_def', 0), 1)}/{round(sH.get('adj_def', 0), 1)}"
            
            ffA = sA.get('four_factors', {})
            ffH = sH.get('four_factors', {})
            
            efg_str = f"{round(ffA.get('efg', 0), 1)}/{round(ffH.get('efg', 0), 1)}"
            to_str = f"{round(ffA.get('tov', 0), 1)}/{round(ffH.get('tov', 0), 1)}"
            or_str = f"{round(ffA.get('orb', 0), 1)}/{round(ffH.get('orb', 0), 1)}"
            ftr_str = f"{round(ffA.get('ftr', 0), 1)}/{round(ffH.get('ftr', 0), 1)}"
            
            print(f"{match_str:<35} | {score_str:<15} | {spread_str:<8} | {conf_str:<10} | {t_str:<11} | {oe_str:<12} | {de_str:<12} | {efg_str:<12} | {to_str:<12} | {or_str:<12} | {ftr_str:<12}")

if __name__ == "__main__":
    main()
