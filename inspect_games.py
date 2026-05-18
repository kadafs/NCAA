import json
import os

pred_path = os.path.join('data', 'basketball', 'universal_predictions_2026-05-16.json')
data = json.load(open(pred_path, encoding='utf-8'))

# Find Pesaro and Nancy U21 games
for p in data['predictions']:
    home = p.get('home_team', '')
    away = p.get('away_team', '')
    matchup = f"{away} @ {home}"
    
    if 'Pesaro' in home or 'Pesaro' in away or 'Rimini' in home or 'Rimini' in away:
        print(f"[SERIE A2] {matchup}")
        print(f"  stage: '{p.get('stage', 'N/A')}'")
        print(f"  model_total: {p.get('model_total')}")
        print(f"  league_id: {p.get('league_id')}")
        print()
    
    if 'Nancy' in home or 'Nancy' in away or 'Saint Quentin' in home or 'Saint Quentin' in away:
        print(f"[ESPOIRS U21] {matchup}")
        print(f"  stage: '{p.get('stage', 'N/A')}'")
        print(f"  model_total: {p.get('model_total')}")
        print(f"  league_id: {p.get('league_id')}")
        print()
