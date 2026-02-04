# verify_ncaa_drop.py
import sys
import os
import json

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.basketball_engine import UniversalBasketballEngine

def test_ncaa_smart_injuries():
    config_path = os.path.join('configs', 'leagues', 'ncaa.json')
    
    # Simulate a generic NCAA game
    game_data = {
        "name": "NCAA",
        "market_total": 145.5,
        "pace_adjustment": 70.0,
        "efficiency_adjustment": 105.0,
        "statsA": {"adj_off": 110.0},
        "statsH": {"adj_off": 110.0},
        "projected_spread": 5.0,
        "conf": "DEFAULT",
        "is_neutral": False
    }
    
    # Case 1: Star Out (AJ Dybantsa - 23.6 PPG)
    # The engine expects raw injuries, but bridge filters them. 
    # Here we test engine behavior with the NEW ncaa.json weights.
    star_injuries = [{"player": "AJ Dybantsa", "status": "Out"}]
    
    # Case 2: Mass Bench Out (5 players)
    mass_injuries = [
        {"player": "Bench 1", "status": "Out"},
        {"player": "Bench 2", "status": "Out"},
        {"player": "Bench 3", "status": "Out"},
        {"player": "Bench 4", "status": "Out"},
        {"player": "Bench 5", "status": "Out"}
    ]
    
    engine = UniversalBasketballEngine(config_path, mode="full")
    
    print("\n--- NCAA Star Injury Test (-1.8 per player) ---")
    res_star = engine.calculate_total(game_data, star_injuries)
    print(f"Total with 1 Star Out: {res_star['final_model_total']}")
    for t in res_star['trace']:
        if "Context Impact" in t: print(f"  {t}")

    print("\n--- NCAA Mass Injury Test (Cap @ 6.5) ---")
    res_mass = engine.calculate_total(game_data, mass_injuries)
    print(f"Total with 5 Out: {res_mass['final_model_total']}")
    for t in res_mass['trace']:
        if "capped" in t or "Context Impact" in t: print(f"  {t}")

    print("\n--- NCAA Bridge Filter Test (Smart Selection) ---")
    # Mock individual_stats logic from universal_bridge.py
    ncaa_pts_map = {"aj dybantsa": 23.6, "bench 1": 2.0}
    raw_injuries = [
        {"player": "AJ Dybantsa", "status": "Out"},
        {"player": "Bench 1", "status": "Out"}
    ]
    # Simulate filtering
    filtered = [i for i in raw_injuries if ncaa_pts_map.get(i['player'].lower(), 0) >= 8.0]
    
    print(f"Raw Injuries: {[i['player'] for i in raw_injuries]}")
    print(f"Filtered Injuries (PPG >= 8.0): {[i['player'] for i in filtered]}")
    
    res_filtered = engine.calculate_total(game_data, filtered)
    print(f"Final Impact (Only Star): {res_filtered['final_model_total']}")
    for t in res_filtered['trace']:
        if "Context Impact" in t: print(f"  {t}")

if __name__ == "__main__":
    test_ncaa_smart_injuries()
