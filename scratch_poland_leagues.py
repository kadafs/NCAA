import json, glob
for f in glob.glob('configs/leagues/*.json'):
    try:
        d = json.load(open(f, encoding='utf-8'))
        if 'poland' in d.get('country', '').lower():
            print(f'League ID: {f} | Name: {d.get("name", "")}')
    except: pass
