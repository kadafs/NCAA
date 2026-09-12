import json, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')

for f in sorted(glob.glob('data/football/universal_predictions_*.json')):
    try:
        data = json.load(open(f, 'r', encoding='utf-8'))
        for p in data.get('predictions', []):
            if p.get('home_team') == 'Aston Villa':
                print(f"Found in {f}: vs {p.get('away_team')}")
                print(f"  xg_h={p.get('xg_home')}, xg_a={p.get('xg_away')}, xg_total={p.get('xg_total')}")
                print(f"  market_odds: {p.get('market_odds')}")
                print(f"  statsH: {p.get('match_center', {}).get('statsH')}")
    except Exception as e:
        print(f"Error {f}: {e}")
