import json
import glob
import os

def update_tier(lid, new_tier):
    path = f'configs/leagues/{lid}.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        d['_tier'] = new_tier
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=2)
        print(f'Fixed League {lid} ({d.get("name", "")}) -> {new_tier}')

update_tier('68', 'top_domestic')
update_tier('258', 'top_domestic')

print('\n--- ALL SECOND DIVISION & LOWER LEAGUES ---')
lower = []
second = []
for f in glob.glob('configs/leagues/*.json'):
    try:
        d = json.load(open(f, encoding='utf-8'))
        tier = d.get('_tier', '')
        name = d.get('name', 'Unknown')
        country = d.get('country', 'Unknown')
        entry = f'{country} - {name} (ID: {os.path.basename(f).replace(".json", "")})'
        if tier == 'lower': lower.append(entry)
        elif tier == 'second_division': second.append(entry)
    except: pass

print('\nSECOND DIVISION:')
for l in sorted(second): print('  ' + l)

print('\nLOWER:')
for l in sorted(lower): print('  ' + l)
