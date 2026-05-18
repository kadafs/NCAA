import json, sys, os
sys.path.insert(0, '.')
from run_confidence_report import load_leaderboard, get_team_stats
from core.confidence_score import compute_confidence

lb = load_leaderboard()

games = [
    ("Nancy U21",      "Saint Quentin U21", 233, 13.06, 11.54, 3.0),
    ("Rimini",         "Pesaro",            242, 17.17, 9.48,  3.0),
]

print(f"\n{'='*80}")
print(f"  CONFIDENCE ENGINE TRACE — WITH HIT RATE")
print(f"{'='*80}")

for home, away, lid, vol_h, vol_a, spread in games:
    mae_h, bias_h, graded_h, ff_h, ff_total_h, src_h = get_team_stats(home, lid, lb)
    mae_a, bias_a, graded_a, ff_a, ff_total_a, src_a = get_team_stats(away, lid, lb)

    game = {
        "vol_a": vol_a, "vol_b": vol_h,
        "mae_a": mae_a, "mae_b": mae_h,
        "bias_a": bias_a, "bias_b": bias_h,
        "spread": spread,
        "hit_rate_a": ff_a, "hit_rate_b": ff_h,
        "hit_rate_games_a": ff_total_a, "hit_rate_games_b": ff_total_h,
    }
    r = compute_confidence(game)

    hr_a_pct = f"{ff_a*100:.1f}%" if ff_a is not None else "N/A"
    hr_h_pct = f"{ff_h*100:.1f}%" if ff_h is not None else "N/A"
    weighted_hr_pct = f"{r['weighted_hit_rate']*100:.1f}%" if r['weighted_hit_rate'] is not None else "neutral"

    print(f"\n  {away} @ {home}  (League {lid})")
    print(f"  {'Home '+home+':':30} MAE={mae_h:.2f}  Vol={vol_h:.2f}  HitRate={hr_h_pct} ({ff_total_h} games)")
    print(f"  {'Away '+away+':':30} MAE={mae_a:.2f}  Vol={vol_a:.2f}  HitRate={hr_a_pct} ({ff_total_a} games)")
    print(f"  weighted_hit_rate used = {weighted_hr_pct}")
    print(f"  Vol={r['vol_score']:>2}/18  MAE={r['mae_score']:>2}/20  Bias={r['bias_score']:>2}/20  Sprd={r['spread_score']:>2}/10  HitRate={r['hit_rate_score']:>2}/32")
    print(f"  Raw={r['raw_score']}/100  Score={r['confidence_score']}  {r['band']['label']}")
