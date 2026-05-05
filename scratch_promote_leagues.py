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
        print(f'Promoted: League {lid} ({d.get("country", "Unknown")} - {d.get("name", "")}) -> {new_tier}')

update_tier('275', 'top_domestic')
update_tier('388', 'top_domestic')

print('\n--- ALL REMAINING SECOND DIVISION LEAGUES ---')
second_leagues = []
for f in glob.glob('configs/leagues/*.json'):
    try:
        d = json.load(open(f, encoding='utf-8'))
        tier = d.get('_tier', '')
        if tier == 'second_division':
            name = d.get('name', 'Unknown')
            country = d.get('country', 'Unknown')
            lid = os.path.basename(f).replace('.json', '')
            second_leagues.append(f'  {country} - {name} (ID: {lid})')
    except: pass

for l in sorted(second_leagues):
    print(l)
