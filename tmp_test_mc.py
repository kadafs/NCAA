import json
data = json.load(open('C:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/data/basketball/universal_predictions_2026-03-21.json', encoding='utf-8'))

for g in data.get('matches', []):
    mc = g.get('match_center', {})
    h2h = mc.get('h2h', [])
    rH = mc.get('recentH', [])
    
    # We want to check if ANY game populated the Match Center natively. 
    # Usually Proballers games have robust matches.
    if len(h2h) > 0 or len(rH) > 0:
        print(f"Verified Game: {g['away_team']} @ {g['home_team']}")
        print(f"  H2H Count: {len(h2h)}")
        print(f"  Recent Form H Count: {len(rH)}")
        if rH:
            print(f"  Sample Recent Form (Team): {rH[0]['teams']['home']['name']} vs {rH[0]['teams']['away']['name']}")
        break
        
print("Dry scan complete.")
