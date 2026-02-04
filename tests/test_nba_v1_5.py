# test_nba_v1_5.py
import sys
import os
import json

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.basketball_engine import UniversalBasketballEngine

def test_nba_modifiers():
    config_path = os.path.join('configs', 'leagues', 'nba.json')
    
    # 1. Test SAFE Mode (Modifiers should NOT trigger)
    engine_safe = UniversalBasketballEngine(config_path, mode="safe")
    
    # Scenario: Elite Offense Shootout + Spread
    game_data = {
        "market_total": 230.0,
        "pace_adjustment": 102.0,
        "efficiency_adjustment": 115.0,
        "statsA": {"adj_off": 125.0}, # High offense
        "statsH": {"adj_off": 125.0}, # High offense
        "projected_spread": 15.0,     # Blowout
        "conf": "NBA",
        "is_neutral": False
    }
    
    res_safe = engine_safe.calculate_total(game_data)
    print(f"\n--- NBA SAFE Mode Test ---")
    print(f"Final Total: {res_safe['final_model_total']}")
    # Check trace to ensure no situational boosters
    situational_triggered = any("Sharp NBA 5" in msg for msg in res_safe['trace'])
    print(f"Situational Modifiers Triggered: {situational_triggered}")

    # 2. Test FULL Mode (Modifiers SHOULD trigger)
    engine_full = UniversalBasketballEngine(config_path, mode="full")
    res_full = engine_full.calculate_total(game_data)
    print(f"\n--- NBA FULL Mode Test (Elite + Blowout) ---")
    print(f"Final Total: {res_full['final_model_total']}")
    
    elite_triggered = any("Sharp NBA 5A" in msg for msg in res_full['trace'])
    blowout_triggered = any("Sharp NBA 5B" in msg for msg in res_full['trace'])
    
    print(f"Elite Offense Triggered: {elite_triggered}")
    print(f"Blowout Triggered: {blowout_triggered}")
    
    # 3. Test Close Game Foul Modifier
    game_data_close = game_data.copy()
    game_data_close["projected_spread"] = 2.0
    res_close = engine_full.calculate_total(game_data_close)
    print(f"\n--- NBA FULL Mode Test (Close Game) ---")
    close_triggered = any("Sharp NBA 5C" in msg for msg in res_close['trace'])
    print(f"Close Game Foul Triggered: {close_triggered}")
    print(f"Trace Sample: {[m for m in res_close['trace'] if 'Sharp NBA 5' in m]}")

if __name__ == "__main__":
    test_nba_modifiers()
