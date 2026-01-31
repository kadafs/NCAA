from core.basketball_engine import UniversalBasketballEngine
import json

def debug_game():
    config_path = "configs/leagues/ncaa.json"
    
    # Simulated Georgia Southern @ Louisiana Monroe data from pusher trace
    game_data = {
        "team": "Georgia Southern",
        "opponent": "Louisiana Monroe",
        "conf": "SB",
        "market_total": 155.5,
        "pace_adjustment": 70.7,
        "efficiency_adjustment": 110.4,
        "projected_spread": 1.6, # Trigger Close Game bonus
        "is_elite_offense": False,
        "is_strong_defense": False,
        "is_neutral": False
    }
    
    print("--- Testing Mode: SAFE ---")
    engine_safe = UniversalBasketballEngine(config_path, mode="safe")
    res_safe = engine_safe.calculate_total(game_data)
    print(f"Legacy Result: {res_safe['legacy_total']}")
    print(f"Sharp Result: {res_safe['sharp_total']}")
    print(f"Decision: {res_safe['decision']}")
    print("Trace:")
    for line in res_safe['trace']:
        print(f"  {line}")

    print("\n--- Testing Mode: FULL ---")
    engine_full = UniversalBasketballEngine(config_path, mode="full")
    res_full = engine_full.calculate_total(game_data)
    print(f"Legacy Result: {res_full['legacy_total']}")
    print(f"Sharp Result: {res_full['sharp_total']}")
    print(f"Decision: {res_full['decision']}")
    print("Trace:")
    for line in res_full['trace']:
        print(f"  {line}")

if __name__ == "__main__":
    debug_game()
