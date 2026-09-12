import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('data/football/universal_predictions_2026-09-10.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data.get('predictions', []):
    if p.get('home_team') == 'Aston Villa':
        print("Aston Villa prediction found in 2026-09-10:")
        print("btts_prob:", p.get('btts_prob'))
        print("over_2_5_prob:", p.get('over_2_5_prob'))
        print("xg_home:", p.get('xg_home'), "xg_away:", p.get('xg_away'), "xg_total:", p.get('xg_total'))
        print("market_odds:", json.dumps(p.get('market_odds'), indent=2))
        print("match_center.statsH:", json.dumps(p.get('match_center', {}).get('statsH'), indent=2))
        print("match_center.statsA:", json.dumps(p.get('match_center', {}).get('statsA'), indent=2))
        break
else:
    print("Aston Villa not found in 2026-09-10")
