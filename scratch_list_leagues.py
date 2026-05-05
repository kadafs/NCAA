import json, glob

leagues = []
for f in glob.glob('configs/leagues/*.json'):
    try:
        d = json.load(open(f, encoding='utf-8'))
        tier = d.get('_tier')
        if tier in ['second_division', 'lower']:
            lid = d.get('_league_id', f.replace('configs/leagues/', '').replace('.json', ''))
            name = d.get('name', 'Unknown')
            country = d.get('country', 'Unknown')
            leagues.append(f"{country} — {name} [ID: {lid}, Tier: {tier}]")
    except:
        pass

print(f"Total: {len(leagues)} leagues\n")
for l in sorted(leagues):
    print(l)
