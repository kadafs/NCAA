import sys
import os
# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.basketball_engine import UniversalBasketballEngine

def test_ncaa_transparency():
    config_path = "configs/leagues/ncaa.json"
    
    # Mock NCAA data: Elite Offense, Blowout
    game_data = {
        "team": "Duke",
        "opponent": "Kentucky",
        "pace_adjustment": 72.0,
        "efficiency_adjustment": 115.0,
        "market_total": 150.0,
        "is_elite_offense": True,
        "projected_spread": 12.0, # Blowout
        "statsA": {"adj_off": 119.0}, # Trigger Elite Offense (>118)
        "statsH": {"adj_off": 119.0},
        "conf": "DEFAULT"
    }
    
    injury_notes = [
        {"player": "Center", "status": "Out"}
    ]
    
    engine_full = UniversalBasketballEngine(config_path, mode="full")
    res = engine_full.calculate_total(game_data, injury_notes)
    
    print(f"--- NCAA FULL Mode Transparency Test ---")
    print(f"Model Total: {res['final_model_total']}")
    print(f"Notes found: {len(res['notes'])}")
    for note in res['notes']:
        print(f"  - {note}")
        
    # Check for expected notes
    expected = ["Elite Offense", "Blowout", "Context Impact"]
    for e in expected:
        found = any(e in n for n in res['notes'])
        if found:
            print(f"SUCCESS: Found expected note containing '{e}'")
        else:
            print(f"FAILURE: Missing expected note containing '{e}'")

if __name__ == "__main__":
    test_ncaa_transparency()
