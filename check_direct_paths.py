import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

paths = [
    'data/football/universal_39_stats.json',
    'data/football/epl_stats.json',
    'data/football/standings_39_2026.json',
    'data/football/standings_39_2025.json',
    'data/football/standings_39_2024.json',
    '../Sports Analytics/public/data/football/universal_39_stats.json',
    '../Sports Analytics/public/data/football/epl_stats.json',
]

for p in paths:
    if os.path.exists(p):
        print(f"Exists: {p} ({os.path.getsize(p)} bytes)")
        try:
            d = json.load(open(p, 'r', encoding='utf-8'))
            if 'teams' in d:
                print("  teams count:", len(d['teams']))
                for k, v in list(d['teams'].items())[:5]:
                    print(f"    {k}: played_all={v.get('played_all')}, season={v.get('season')}")
            elif 'response' in d:
                print("  response len:", len(d['response']))
        except Exception as e:
            print("  err:", e)
    else:
        print(f"Does not exist: {p}")
