# test_ncaa_v1_4.py
import sys
import os
import json

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.basketball_engine import UniversalBasketballEngine

def test_v1_4():
    config_path = "configs/leagues/ncaa.json"
    engine_full = UniversalBasketballEngine(config_path, mode="full")
    engine_safe = UniversalBasketballEngine(config_path, mode="safe")

    tests = [
        {
            "name": "Small Edge Pass (< 4.0)",
            "data": {
                "market_total": 145.0, # Resulting model is ~141, edge ~3.5-4.0
                "pace_adjustment": 68.0,
                "efficiency_adjustment": 105.0,
                "projected_spread": 10.0,
                "conf": "DEFAULT",
                "statsA": {"adj_off": 110.0, "adj_def": 110.0, "adj_t": 70.0},
                "statsH": {"adj_off": 110.0, "adj_def": 110.0, "adj_t": 70.0}
            },
            "expect_decision": "PASS",
            "expect_confidence": "NO PLAY"
        },
        {
            "name": "Elite Offense Shootout (+3.0)",
            "data": {
                "market_total": 150.0,
                "pace_adjustment": 70.0,
                "efficiency_adjustment": 105.0,
                "projected_spread": 10.0,
                "conf": "DEFAULT",
                "statsA": {"adj_off": 125.0, "adj_def": 110.0, "adj_t": 70.0},
                "statsH": {"adj_off": 125.0, "adj_def": 110.0, "adj_t": 70.0}
            }
        },
        {
            "name": "Blowout Volatility Under Penalty (+3.5)",
            "data": {
                "market_total": 160.0,
                "pace_adjustment": 68.0,
                "efficiency_adjustment": 105.0,
                "projected_spread": 12.0, # Blowout
                "conf": "DEFAULT",
                "statsA": {"adj_off": 100.0, "adj_def": 110.0, "adj_t": 68.0},
                "statsH": {"adj_off": 100.0, "adj_def": 110.0, "adj_t": 68.0}
            }
        },
        {
            "name": "Late-Game Foul Inflation (+3.0)",
            "data": {
                "market_total": 145.0,
                "pace_adjustment": 68.0,
                "efficiency_adjustment": 105.0,
                "projected_spread": 2.0, # Tight
                "conf": "DEFAULT",
                "statsA": {"adj_off": 110.0, "adj_def": 110.0, "adj_t": 70.0},
                "statsH": {"adj_off": 110.0, "adj_def": 110.0, "adj_t": 70.0}
            }
        }
    ]

    for t in tests:
        print(f"\n--- Running Test: {t['name']} ---")
        res = engine_full.calculate_total(t['data'])
        print(f"  Model Total: {res['final_model_total']}")
        print(f"  Edge: {res['edge']}")
        print(f"  Decision: {res['decision']}")
        print(f"  Confidence: {res['confidence']}")
        if 'notes' in res and res['notes']:
            print(f"  Notes: {res['notes']}")
        
        for trace in res['trace']:
            if "Sharp" in trace:
                print(f"    {trace}")

        if 'expect_decision' in t:
            assert res['decision'] == t['expect_decision'], f"Failed decision: {res['decision']} != {t['expect_decision']}"
        if 'expect_confidence' in t:
            assert res['confidence'] == t['expect_confidence'], f"Failed confidence: {res['confidence']} != {t['expect_confidence']}"

    # Verify Safe Mode has NO Trace for Sharp
    print("\n--- Running Safe Mode Verification ---")
    res_safe = engine_safe.calculate_total(tests[1]['data'])
    sharp_trace = [tr for tr in res_safe['trace'] if "Sharp" in tr]
    print(f"  Sharp Trace Count: {len(sharp_trace)}")
    assert len(sharp_trace) == 0, "Safe mode should not have sharp traces"

    print("\n[OK] All tests passed!")

if __name__ == "__main__":
    test_v1_4()
