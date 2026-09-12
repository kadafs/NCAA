import json, sys
sys.stdout.reconfigure(encoding='utf-8')

p = 'data/football/universal_39_stats.json'
d = json.load(open(p, 'r', encoding='utf-8'))
print("Teams in universal_39_stats.json:")
for tname, s in d.get('teams', {}).items():
    print(f"  {tname:20}: season={s.get('season')}, played_all={s.get('played_all')}, form='{s.get('form')}'")
    prev = s.get('previous_season')
    if prev:
        print(f"       prev_season: season={prev.get('season')}, played_all={prev.get('played_all')}")
