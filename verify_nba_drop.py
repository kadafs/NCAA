# verify_nba_drop.py
import sys
import os
import json

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.basketball_engine import UniversalBasketballEngine

def test_nba_nuggets_drop():
    config_path = os.path.join('configs', 'leagues', 'nba.json')
    
    # Simulate Nuggets vs Knicks
    game_data = {
        "name": "NBA",
        "market_total": 226.5,
        "pace_adjustment": 102.5,
        "efficiency_adjustment": 115.0, 
        "statsA": {"adj_off": 121.0}, # nuggets (elite)
        "statsH": {"adj_off": 116.0}, # knicks (elite-ish)
        "projected_spread": 5.0,
        "conf": "NBA",
        "is_neutral": False,
        "is_rebound_mismatch": False,
        "is_turnover_mismatch": False,
        "three_pa_total": 75
    }
    
    # 5 Players Out as seen in the drop
    injury_notes = [
        {"player": "Player 1", "status": "Out"},
        {"player": "Player 2", "status": "Out"},
        {"player": "Player 3", "status": "Out"},
        {"player": "Player 4", "status": "Out"},
        {"player": "Player 5", "status": "Out"}
    ]
    
    # Test SAFE Mode
    engine_safe = UniversalBasketballEngine(config_path, mode="safe")
    res_safe = engine_safe.calculate_total(game_data, [])
    print(f"\n--- SAFE Mode ---")
    print(f"Total: {res_safe['final_model_total']}")
    
    # Test FULL Mode
    engine_full = UniversalBasketballEngine(config_path, mode="full")
    res_full = engine_full.calculate_total(game_data, injury_notes)
    print(f"\n--- FULL Mode ---")
    print(f"Total: {res_full['final_model_total']}")
    print("\nTrace:")
    for t in res_full['trace']:
        print(f"  {t}")

if __name__ == "__main__":
    test_nba_nuggets_drop()
