import sys
import os
# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.basketball_engine import UniversalBasketballEngine

def test_safe_vs_full():
    config_path = "configs/leagues/nba.json"
    
    # Mock data: High Pace, Elite Offense, but with Injuries
    game_data = {
        "team": "Lakers",
        "opponent": "Celtics",
        "pace_adjustment": 102.0,
        "efficiency_adjustment": 118.0,
        "market_total": 230.0,
        "is_elite_offense": True,
        "is_strong_defense": False,
        "three_pa_total": 85,
        "projected_spread": 2.0, # Close game
        "statsA": {"adj_off": 120.0},
        "statsH": {"adj_off": 120.0},
        "conf": "DEFAULT"
    }
    
    # 3 major starters out
    injury_notes = [
        {"player": "A", "status": "Out"},
        {"player": "B", "status": "Out"},
        {"player": "C", "status": "Out"}
    ]
    
    engine_safe = UniversalBasketballEngine(config_path, mode="safe")
    engine_full = UniversalBasketballEngine(config_path, mode="full")
    
    res_safe = engine_safe.calculate_total(game_data, injury_notes)
    res_full = engine_full.calculate_total(game_data, injury_notes)
    
    print(f"--- Safe Mode ---")
    print(f"Total: {res_safe['final_model_total']}")
    # print(f"Trace: {res_safe['trace']}")
    
    print(f"\n--- Full Mode ---")
    print(f"Total: {res_full['final_model_total']}")
    print(f"Notes: {res_full['notes']}")
    
    if res_safe['final_model_total'] > res_full['final_model_total']:
        print("\nWARNING: Safe Total is HIGHER than Full Total!")
        print("Trace explanation:")
        for log in res_full['trace']:
            if "Stats Baseline" in log or "Sharp" in log or "Impact" in log:
                print(f"  {log}")
    else:
        print("\nSUCCESS: Full Total is >= Safe Total.")

if __name__ == "__main__":
    test_safe_vs_full()
