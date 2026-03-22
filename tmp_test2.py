import json

with open('C:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/data/basketball/universal_predictions_2026-03-21.json', encoding='utf-8') as f:
    data = json.load(f)

for g in data:
    mc = g.get('match_center', {})
    h2h = mc.get('h2h', [])
    rH = mc.get('recentH', [])
    
    if len(h2h) > 0 or len(rH) > 0:
        print(f"Verified Game: {g.get('away_team')} @ {g.get('home_team')}")
        print(f"  H2H Count: {len(h2h)}")
        print(f"  Recent Form H Count: {len(rH)}")
        if rH:
            print(f"  Sample Recent Form (Team): {rH[0].get('teams', {}).get('home', {}).get('name')}")
        break
        
print("Execution valid.")
