import sys
import os
# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.basketball_engine import UniversalBasketballEngine

def test_ncaa_transparency():
    config_path = "configs/leagues/ncaa.json"
    
def test_scenario(label, game_data):
    print(f"\n--- {label} ---")
    engine = UniversalBasketballEngine("configs/leagues/ncaa.json", mode="full")
    res = engine.calculate_total(game_data)
    print(f"Total: {res['final_model_total']} | Conf: {res['confidence']}")
    print(f"Notes: {res['notes']}")
    for log in res['trace']:
        if "Sharp" in log or "Gate" in log or "Stats Baseline" in log:
            print(f"  {log}")

# Scenario 1: SEC Power Game (Blowout + Elite Offense + High Pace)
s1_data = {
    "team": "Alabama", "opponent": "Kentucky",
    "pace_adjustment": 78.0, "efficiency_adjustment": 120.0,
    "market_total": 160.0, "is_elite_offense": True,
    "projected_spread": 15.0, "conf": "SEC",
    "statsA": {"adj_off": 125.0}, "statsH": {"adj_off": 125.0}
}
test_scenario("SEC Elite Blowout (Tests Gates)", s1_data)

# Scenario 2: Mid-major Close Game (Small Edge, NO elite, Close Game)
s2_data = {
    "team": "Toledo", "opponent": "Akron",
    "pace_adjustment": 68.0, "efficiency_adjustment": 105.0,
    "market_total": 142.0, "is_elite_offense": False,
    "projected_spread": 2.0, "conf": "DEFAULT",
    "statsA": {"adj_off": 105.0}, "statsH": {"adj_off": 105.0}
}
test_scenario("Mid-major Close Game (Tests Foul Bonus LAST)", s2_data)

if __name__ == "__main__":
    test_ncaa_transparency()
