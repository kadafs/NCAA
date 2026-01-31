from core.basketball_engine import UniversalBasketballEngine
import json

def debug_nba():
    config_path = "configs/leagues/nba.json"
    
    # Typical NBA Matchup
    game_data = {
        "team": "Lakers",
        "opponent": "Celtics",
        "conf": "DEFAULT",
        "market_total": 230.5,
        "pace_adjustment": 102.5,
        "efficiency_adjustment": 118.0,
        "is_elite_offense": True,
        "is_strong_defense": False,
        "three_pt_freq_ratio": 0.45 # Trigger Sharp 3PT
    }
    
    print("--- Testing NBA Mode: SAFE ---")
    engine_safe = UniversalBasketballEngine(config_path, mode="safe")
    res_safe = engine_safe.calculate_total(game_data)
    print(f"Legacy Result: {res_safe['legacy_total']}")
    print("Trace Content:")
    for line in res_safe['trace']:
        print(f"  {line}")

    print("\n--- Testing NBA Mode: FULL ---")
    engine_full = UniversalBasketballEngine(config_path, mode="full")
    res_full = engine_full.calculate_total(game_data)
    print(f"Sharp Result: {res_full['sharp_total']}")
    print("Trace Content:")
    for line in res_full['trace']:
        print(f"  {line}")

if __name__ == "__main__":
    debug_nba()
