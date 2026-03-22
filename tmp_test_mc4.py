import json

with open('data/basketball/universal_predictions_2026-03-22.json', encoding='utf-8') as f:
    d = json.load(f)

found_h2h = 0
found_recent = 0
print(f"Total Games: {len(d.get('predictions', []))}")

for g in d.get('predictions', []):
    mc = g.get('match_center', {})
    if len(mc.get('h2h', [])) > 0: found_h2h += 1
    if len(mc.get('recentH', [])) > 0: found_recent += 1
    if 'Opava' in g.get('home_team', '') or 'Opava' in g.get('away_team', '') or 'Holbaek' in g.get('home_team', ''):
        print(f"\nTarget Game: {g.get('away_team')} @ {g.get('home_team')}")
        print(f" -> H2H: {len(mc.get('h2h', []))}, RecentH: {len(mc.get('recentH', []))}")
        if mc.get('full_standings') and len(mc.get('full_standings')) > 0 and len(mc.get('full_standings')[0]) > 0:
            print(f" -> Standings populated! Sample rank: {mc.get('full_standings')[0][0].get('position')} - {mc.get('full_standings')[0][0].get('team', {}).get('name')}")
            
print(f"\nGames with offline H2H globally: {found_h2h}")
print(f"Games with offline Recent Form globally: {found_recent}")
