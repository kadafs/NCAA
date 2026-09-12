import json, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')

for root in [r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\public\data\football', r'c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\football']:
    for f in glob.glob(os.path.join(root, 'universal_predictions_*.json')):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            for p in data.get('predictions', []):
                if p.get('home_team') == 'Aston Villa' and p.get('away_team') == 'Nottingham Forest':
                    print(f"MATCH FOUND in {f}:")
                    print(json.dumps(p, indent=2))
                    sys.exit(0)
        except Exception as e:
            print(f"Error reading {f}: {e}")
