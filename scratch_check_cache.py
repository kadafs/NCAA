import json
import glob

files = glob.glob('data/api_basketball_today_*.json')
for f in files:
    with open(f, encoding='utf-8') as file:
        data = json.load(file)
        for lg in data.get('leagues_summary', []):
            if lg.get('games'):
                print(f"File: {f}")
                print(json.dumps(lg['games'][0], indent=2))
                exit()
