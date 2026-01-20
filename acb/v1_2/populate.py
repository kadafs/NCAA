import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from acb.fetch_acb_schedule import fetch_acb_schedule
from acb.fetch_acb_stats import fetch_acb_stats
from utils.mapping import get_target_date

def get_daily_input_sheet(date_obj=None, refresh=False):
    """
    Standardizes ACB data for the universal prediction engine.
    """
    if refresh:
        # Defaulting to round 5899 as identified in research
        fetch_acb_schedule(date_obj, round_id=5899)
        fetch_acb_stats(round_id=5899)
        
    try:
        with open("data/acb_matchups.json", "r") as f:
            matchups = json.load(f)
        with open("data/acb_stats.json", "r") as f:
            stats = json.load(f)
    except FileNotFoundError:
        print("ACB data files not found. Refreshing...")
        fetch_acb_schedule(date_obj, round_id=5899)
        stats = fetch_acb_stats(round_id=5899)
        with open("data/acb_matchups.json", "r") as f:
            matchups = json.load(f)

    standardized_matchups = []
    
    for m in matchups:
        home_name = m.get("home_team")
        away_name = m.get("away_team")
        
        # In ACB, stats names might need matching if they don't align perfectly with schedule names
        home_stats = stats.get(home_name, {})
        away_stats = stats.get(away_name, {})
        
        if not home_stats or not away_stats:
            print(f"Skipping ACB matchup: {away_name} @ {home_name} (Missing stats)")
            continue
            
        # ACB Specific: Map fields
        # ACB doesn't provide rating directly, we'll use avg_points as Proxies for AdjO/AdjD if needed, 
        # or just PPG/OPPG for the BasketballEngine (which handles them or falls back to rating if provided).
        # Actually BasketballEngine uses adj_o/adj_d. We'll map avg_points to them for now.
        std_matchup = {
            "matchup": f"{m.get('away_tricode')} @ {m.get('home_tricode')}",
            "team": away_name, # Away is 'team'
            "opponent": home_name, # Home is 'opponent'
            "away_team": away_name,
            "home_team": home_name,
            "home_stats": {
                "adj_o": home_stats.get("points_for_average"),
                "adj_d": home_stats.get("points_against_average"),
                "adj_t": 74.0, # ACB Pace Pivot
                "avg_points": home_stats.get("points_for_average"),
                "opp_avg_points": home_stats.get("points_against_average"),
                "wins": home_stats.get("wins"),
                "losses": home_stats.get("losses")
            },
            "away_stats": {
                "adj_o": away_stats.get("points_for_average"),
                "adj_d": away_stats.get("points_against_average"),
                "adj_t": 74.0, # ACB Pace Pivot
                "avg_points": away_stats.get("points_for_average"),
                "opp_avg_points": away_stats.get("points_against_average"),
                "wins": away_stats.get("wins"),
                "losses": away_stats.get("losses")
            },
            "metadata": {
                "league": "ACB",
                "start_time": m.get("start_time"),
                "gravity": 1.0
            }
        }
        standardized_matchups.append(std_matchup)
        
    return standardized_matchups

if __name__ == "__main__":
    sheet = get_daily_input_sheet(refresh=True)
    print(json.dumps(sheet, indent=2))
