import os, json, glob, sys
sys.stdout.reconfigure(encoding='utf-8')

for p in glob.glob('data/football/*39*.json'):
    print(f"File: {p}")
    try:
        data = json.load(open(p, 'r', encoding='utf-8'))
        if isinstance(data, dict):
            print("  Keys:", list(data.keys())[:10])
            if 'teams' in data:
                print("  Teams count:", len(data['teams']))
                for tname, s in list(data['teams'].items())[:3]:
                    print(f"    Team {tname}: played_all={s.get('played_all')}, season={s.get('season')}")
    except Exception as e:
        print("  Error:", e)
