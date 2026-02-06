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
        "pace_adjustment": 112.0, # Very High Pace to test Cap (112-105)*0.2 = 1.4 -> Capped at 1.0?
        # efficiency_adjustment ignored for NBA in v3.1 (uses matchup stats)
        "market_total": 210.0, 
        "is_elite_offense": True,
        "is_strong_defense": False,
        "three_pa_total": 85,
        "projected_spread": 15.0, # Blowout scenario > 12
        # Mock Pace Split logic: Both fast at current venue
        "statsA": {"adj_off": 125.0, "adj_def": 110.0, "pace_away": 105.0, "pace": 100.0},
        "statsH": {"adj_off": 125.0, "adj_def": 110.0, "pace_home": 105.0, "pace": 100.0},
        "conf": "DEFAULT",
        "is_b2b_home": True,      # -1.0
        "is_3in4_away": True      # -2.0 -> Total -3.0
    }
    
    # Tiered Injury Test: 1 MVP out
    injury_notes = [
        {"player": "LeBron", "status": "Out", "note": "MVP candidate out"},
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
    print(f"\nGATE CHECK - High Pace Conflict: {'PASS' if gate_pass else 'FAIL'}")

    # 2. Order Check: Foul Bonus should be LAST sharp adjustment before Anchoring/Clamping
    foul_bonus_idx = -1
    anchor_idx = -1
    for i, line in enumerate(res_full['trace']):
        if "Close Game Foul Bonus (LAST)" in line:
            foul_bonus_idx = i
        if "Market Anchoring" in line:
            anchor_idx = i

    if foul_bonus_idx > -1 and (anchor_idx > foul_bonus_idx or anchor_idx == -1):
        print("ORDER CHECK - Foul Bonus LAST: PASS")
    else:
        print("ORDER CHECK - Foul Bonus LAST: FAIL")

if __name__ == "__main__":
    test_safe_vs_full()
