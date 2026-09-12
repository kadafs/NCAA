import json, glob, sys
sys.stdout.reconfigure(encoding='utf-8')

for f in glob.glob(r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\public\data\football\universal_predictions_*.json'):
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    for p in data.get('predictions', []):
        if p.get('home_team') == 'Aston Villa':
            print(f"Found Aston Villa in {f} on date {p.get('date') or p.get('match_time')}")
            print("p keys:", list(p.keys()))
            print("btts_prob:", p.get('btts_prob'))
            print("over_2_5_prob:", p.get('over_2_5_prob'))
            print("match_center:", p.get('match_center'))
            print("prob_over_2_5 or similar:", {k: v for k, v in p.items() if '2_5' in k or 'over' in k or 'under' in k or 'btts' in k})
            break
