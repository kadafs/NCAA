import json, sys, os, difflib
sys.path.insert(0, os.path.abspath('.'))
from run_confidence_report import load_leaderboard, get_team_stats

lb = load_leaderboard()

# Test the exact lookup the engine performs for the U21 game (league_id=233)
teams = [
    ("Nancy U21", 233),
    ("Saint Quentin U21", 233),
    ("Nancy", 2),
    ("Saint Quentin", 2),
]

for name, lid in teams:
    mae, bias, graded, src = get_team_stats(name, lid, lb)
    print(f"{name:<25} | league_id={lid:<4} | MAE={mae:<7.2f} | Bias={bias:<7.2f} | Graded={graded:<3} | Source={src}")

# Also check what the U21 prediction volatility values are
pred_path = os.path.join('data', 'basketball', 'universal_predictions_2026-05-16.json')
data = json.load(open(pred_path, encoding='utf-8'))
for p in data['predictions']:
    home = p.get('home_team', '')
    away = p.get('away_team', '')
    if 'Nancy U21' in (home, away) or 'Saint Quentin U21' in (home, away):
        print(f"\nU21 Game Volatility Data:")
        print(f"  home_team: {home} | home_vol: {p.get('home_team_volatility')}")
        print(f"  away_team: {away} | away_vol: {p.get('away_team_volatility')}")
        print(f"  model_total: {p.get('model_total')}")
        print(f"  league_id: {p.get('league_id')}")
