import os
import json
from core.basketball_engine import UniversalBasketballEngine

def test_safe_mode_absolute_edge():
    config_path = os.path.abspath("configs/leagues/ncaa.json")
    # Initialize in SAFE mode
    engine_safe = UniversalBasketballEngine(config_path, mode="safe")

    # Test Case: Under Edge
    # Market: 150, Model: 140 -> -10 edge
    # Expected in SAFE: abs_edge=10.0, side=UNDER, confidence=HIGH
    game_data = {
        'game_id': 'test_safe_under',
        'market_total': 150.0,
        'pace_adjustment': 68.0, # Pivot
        'efficiency_adjustment': 105.0, # Pivot
        'is_neutral': True
    }
    
    # Raw math: ((105 * 68) / 100) * 2 = 142.8
    # Regression: 142.8 * 0.97 = 138.52
    # Regression total: 138.52
    # Market: 150.0
    # Edge: -11.48
    # Abs Edge: 11.48
    
    res = engine_safe.calculate_total(game_data)
    
    print("\n--- SAFE MODE ABSOLUTE EDGE TEST ---")
    print(f"Market: {res['market_total']}")
    print(f"Final Model Total: {res['final_model_total']}")
    print(f"Edge: {res['edge']}")
    print(f"Abs Edge: {res['abs_edge']}")
    print(f"Side: {res['side']}")
    print(f"Confidence: {res['confidence']}")
    print(f"Decision: {res['decision']}")

    assert res['side'] == "UNDER"
    assert res['abs_edge'] > 10.0
    assert res['confidence'] == "HIGH"
    print("\nSUCCESS: SAFE mode now respects Absolute Edge logic.")

if __name__ == "__main__":
    test_safe_mode_absolute_edge()
