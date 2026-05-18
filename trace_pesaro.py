import json, os, sys
sys.path.insert(0, '.')
from run_confidence_report import load_leaderboard, get_team_stats
from core.confidence_score import compute_confidence

lb = load_leaderboard()

# Trace Pesaro @ Rimini exactly as the engine sees it today
home, away = "Rimini", "Pesaro"
league_id = 242

mae_h, bias_h, graded_h, src_h = get_team_stats(home, league_id, lb)
mae_a, bias_a, graded_a, src_a = get_team_stats(away, league_id, lb)

# From the prediction JSON
vol_h = 17.17   # Pesaro (home per today's game) -- actually away today
vol_a = 9.48    # Rimini

print("=== Pesaro @ Rimini (today, league 242, playoff) ===")
print(f"  Home: {home} | MAE={mae_h:.2f} | Bias={bias_h:.2f} | Graded={graded_h} | Src={src_h}")
print(f"  Away: {away} | MAE={mae_a:.2f} | Bias={bias_a:.2f} | Graded={graded_a} | Src={src_a}")
print(f"  vol_h (Pesaro today as away): {vol_a}  vol_a (Rimini today as home): {vol_h}")
print(f"  max_vol = max({vol_h}, {vol_a}) = {max(vol_h, vol_a)}")
print(f"  max_mae = max({mae_h:.2f}, {mae_a:.2f}) = {max(mae_h, mae_a):.2f}")

game = {
    "vol_a": vol_a, "vol_b": vol_h,
    "mae_a": mae_a, "mae_b": mae_h,
    "bias_a": bias_a, "bias_b": bias_h,
    "spread": 3.0,
}

result = compute_confidence(game)
print(f"\n  max_vol score: {result['vol_score']}/27")
print(f"  max_mae score: {result['mae_score']}/20")
print(f"  bias score:    {result['bias_score']}/20")
print(f"  spread score:  {result['spread_score']}/8")
print(f"  raw:           {result['raw_score']}/75")
print(f"  confidence:    {result['confidence_score']} {result['band']['label']}")
