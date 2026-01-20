import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nbl.fetch_nbl_schedule import fetch_nbl_schedule
from nbl.fetch_nbl_stats import fetch_nbl_stats
from utils.mapping import get_target_date

def get_daily_input_sheet(date_obj=None, refresh=False):
    """
    Standardizes NBL data for the universal prediction engine.
    """
    if refresh:
        fetch_nbl_schedule(date_obj)
        fetch_nbl_stats()
        
    try:
        with open("data/nbl_matchups.json", "r") as f:
            matchups = json.load(f)
        with open("data/nbl_stats.json", "r") as f:
            stats = json.load(f)
    except FileNotFoundError:
        print("NBL data files not found. Refreshing...")
        fetch_nbl_schedule(date_obj)
        stats = fetch_nbl_stats()
        with open("data/nbl_matchups.json", "r") as f:
            matchups = json.load(f)

    standardized_matchups = []
    
    for m in matchups:
        home_name = m.get("home_team")
        away_name = m.get("away_team")
        
        home_stats = stats.get(home_name, {})
        away_stats = stats.get(away_name, {})
        
        # Check if we have enough data to predict
        if not home_stats or not away_stats:
            print(f"Skipping NBL matchup: {away_name} @ {home_name} (Missing stats)")
            continue
            
        # NBL Specific: Map available fields to Universal Engine expectations
        # NBL provides offensive_rating/defensive_rating directly
        std_matchup = {
            "matchup": f"{m.get('away_tricode')} @ {m.get('home_tricode')}",
            "team": away_name, # Away is 'team'
            "opponent": home_name, # Home is 'opponent'
            "away_team": away_name,
            "home_team": home_name,
            "home_stats": {
                "adj_o": home_stats.get("offensive_rating"),
                "adj_d": home_stats.get("defensive_rating"),
                "adj_t": home_stats.get("pace"),
                "avg_points": home_stats.get("points_for_average"),
                "opp_avg_points": home_stats.get("points_against_average"),
                "wins": home_stats.get("wins"),
                "losses": home_stats.get("losses")
            },
            "away_stats": {
                "adj_o": away_stats.get("offensive_rating"),
                "adj_d": away_stats.get("defensive_rating"),
                "adj_t": away_stats.get("pace"),
                "avg_points": away_stats.get("points_for_average"),
                "opp_avg_points": away_stats.get("points_against_average"),
                "wins": away_stats.get("wins"),
                "losses": away_stats.get("losses")
            },
            "metadata": {
                "league": "NBL",
                "start_time": m.get("start_time"),
                "gravity": 1.0 # Standard NBL gravity
            }
        }
        standardized_matchups.append(std_matchup)
        
    return standardized_matchups

if __name__ == "__main__":
    sheet = get_daily_input_sheet(refresh=True)
    print(json.dumps(sheet, indent=2))
