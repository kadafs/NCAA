import os
import json
from core.basketball_engine import UniversalBasketballEngine

def test_ncaa_v21_scenarios():
    config_path = os.path.abspath("configs/leagues/ncaa.json")
    engine_full = UniversalBasketballEngine(config_path, mode="full")

    # Scenario 1: SEC Power Game (Blowout + Elite Offense + High Pace)
    s1_data = {
        'game_id': 'sec_power',
        'home_team': 'Alabama',
        'away_team': 'Kentucky',
        'market_total': 160.0,
        'home_avg_ppg': 85.0,
        'away_avg_ppg': 85.0,
        'home_pace': 78.0,
        'away_pace': 78.0,
        'is_neutral': True,
        'projected_spread': 15.0, # Blowout
        'is_elite_offense': True,
        'nre': 45
    }
    print(f"\n--- SCENARIO 1: SEC Elite Blowout (Tests Gates) ---")
    res_s1 = engine_full.calculate_total(s1_data)
    print(f"Total: {res_s1['final_model_total']} | Conf: {res_s1['confidence']}")
    print(f"Notes: {res_s1['notes']}")
    for log in res_s1['trace']:
        if "Sharp" in log or "Gate" in log:
            print(f"  {log}")

    # Scenario 2: Mid-major Close Game (Small Edge, NO elite, Close Game)
    s2_data = {
        'game_id': 'mid_major_close',
        'home_team': 'Toledo',
        'away_team': 'Akron',
        'market_total': 142.0,
        'home_avg_ppg': 70.0,
        'away_avg_ppg': 70.0,
        'home_pace': 68.0,
        'away_pace': 68.0,
        'is_neutral': False,
        'projected_spread': 2.0, # Close
        'is_elite_offense': False,
        'nre': 40
    }
    print(f"\n--- SCENARIO 2: Mid-major Close Game (Tests Foul Bonus LAST) ---")
    res_s2 = engine_full.calculate_total(s2_data)
    print(f"Total: {res_s2['final_model_total']} | Conf: {res_s2['confidence']}")
    print(f"Notes: {res_s2['notes']}")

    # Scenario 3: v2.1 Structural Volatility Test (Soft Foul + Mid-range Volatility)
    # Competitive Spread (<= 7), Mid-tempo (sharp_total ~150), NRE >= 50
    v21_game = {
        'game_id': 'v21_chaos',
        'home_team': 'Chaos State',
        'away_team': 'Static Tech',
        'market_total': 148.0,
        'pace_adjustment': 70.0,
        'efficiency_adjustment': 110.0,
        'is_neutral': True,
        'projected_spread': 3.5, # Competitive
        'nre': 65 # High volatility
    }
    
    print("\n--- SCENARIO 3: v2.1 STRUCTURAL VOLATILITY (Soft Foul + Mid Boost) ---")
    res_v21 = engine_full.calculate_total(v21_game)
    print(f"Final Total: {res_v21['final_model_total']}")
    print(f"Edge: {res_v21['edge']:.2f}")
    print(f"Confidence: {res_v21['confidence']}")
    print("Trace Analysis:")
    for line in res_v21['trace']:
        print(f"  {line}")
    for note in res_v21['notes']:
        if "Soft Foul" in note or "Mid-range" in note:
            print(f"  [NOTE] {note}")

    # SCENARIO 4: Play Threshold Boundary Test (6.0)
    boundary_game = {
        'game_id': 'boundary',
        'home_team': 'Team A',
        'away_team': 'Team B',
        'market_total': 145.0,
        'pace_adjustment': 70.0,
        'efficiency_adjustment': 108.0,
        'is_neutral': True,
        'projected_spread': 12.0 # No soft foul
    }
    print("\n--- SCENARIO 4: PLAY THRESHOLD BOUNDARY (6.0) ---")
    res_bound = engine_full.calculate_total(boundary_game)
    print(f"Edge: {res_bound['edge']:.2f}, Decision: {res_bound['decision']}, Confidence: {res_bound['confidence']}")
    
    # Assertions for v2.1
    soft_foul_found = any("Soft Foul" in n for n in res_v21['notes'])
    mid_vol_found = any("Mid-range" in n for n in res_v21['notes'])
    
    if soft_foul_found and mid_vol_found:
        print("\nSUCCESS: v2.1 Structural layers triggered correctly.")
    else:
        print(f"\nFAILURE: Missing layers. Soft: {soft_foul_found}, Mid: {mid_vol_found}")

if __name__ == "__main__":
    test_ncaa_v21_scenarios()
