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
        "pace_adjustment": 106.0, # Triggers High Pace (>105)
        "efficiency_adjustment": 125.0, # Elite Offense
        "market_total": 210.0, # Create a large edge for HIGH confidence
        "is_elite_offense": True,
        "is_strong_defense": False,
        "three_pa_total": 85,
        "projected_spread": 2.0, # Close game
        "statsA": {"adj_off": 125.0},
        "statsH": {"adj_off": 125.0},
        "conf": "DEFAULT"
    }
    
    # 3 major starters out
    injury_notes = [
        {"player": "A", "status": "Out"},
        {"player": "B", "status": "Out"}
    ]
    
    engine_safe = UniversalBasketballEngine(config_path, mode="safe")
    engine_full = UniversalBasketballEngine(config_path, mode="full")
    
    res_safe = engine_safe.calculate_total(game_data, injury_notes)
    res_full = engine_full.calculate_total(game_data, injury_notes)
    
    print(f"--- NBA v2.0 Refinement Test ---")
    print(f"Safe Total: {res_safe['final_model_total']}")
    print(f"Full Total: {res_full['final_model_total']}")
    print(f"Confidence Level: {res_full['confidence']} (Edge: {res_full['edge']})")
    print(f"Notes: {res_full['notes']}")
    
    # Trace Analysis
    print("\nTrace Highlights:")
    for log in res_full['trace']:
        if any(x in log for x in ["Sharp", "Gate", "Impact", "Baseline"]):
            print(f"  {log}")
    
    # Logic Checks
    gate_pass = any("High Pace Gate" in log for log in res_full['trace'])
    order_pass = res_full['trace'][-1].startswith("Sharp 9") or "Foul Bonus (LAST)" in res_full['trace'][-1]
    print(f"\nGATE CHECK - High Pace Conflict: {'PASS' if gate_pass else 'FAIL'}")
    print(f"ORDER CHECK - Foul Bonus LAST: {'PASS' if order_pass else 'FAIL'}")

if __name__ == "__main__":
    test_safe_vs_full()
