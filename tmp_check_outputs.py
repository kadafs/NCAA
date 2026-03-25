import json

with open("data/basketball/universal_predictions_2026-03-25.json", encoding="utf-8") as f:
    preds = json.load(f).get("predictions", [])

taca = [p for p in preds if "TACA DA LIGA" in p.get("league", "").upper()]
with_edge = [p for p in preds if p.get("edge") is not None]

print(f"Total Predictions: {len(preds)}")
print(f"Total with Edge: {len(with_edge)}")
print(f"Total Taca Da Liga games: {len(taca)}")

if taca:
    for g in taca:
        print(f"  TACA: {g['away_team']} @ {g['home_team']} -> model={g.get('model_total')} edge={g.get('edge')}")
        
print("\nCheck some skipped edges:")
no_edge = [p for p in preds if p.get("edge") is None][:5]
for g in no_edge:
    print(f"  NO_EDGE: {g['league']} | {g['away_team']} @ {g['home_team']} -> model={g.get('model_total')}")
