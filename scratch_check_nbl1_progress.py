import json, glob, os

files = glob.glob('data/historical/nbl1_official_*.json')
total = 0
for f in sorted(files):
    try:
        data = json.load(open(f, 'r', encoding='utf-8'))
        if isinstance(data, list) and data:
            total += len(data)
            g = data[0]
            fid = g.get('fixture_id', '')
            home = g.get('home_team')
            away = g.get('away_team')
            print(f'{os.path.basename(f)}: {len(data)} real games')
            print(f'  Sample: {home} vs {away}')
            print(f'  fixture_id: {fid}')
            print(f'  Is real UUID: {len(str(fid)) > 10}')
    except Exception as e:
        print(f'{f}: {e}')

cache_path = 'data/historical/nbl1_invalid_uuids.json'
cache = json.load(open(cache_path)) if os.path.exists(cache_path) else []
print()
print(f'Total real games extracted so far: {total}')
print(f'Bad ID cache size: {len(cache)} (UUIDs confirmed invalid)')
