import json, os, glob

DATA_DIR = os.path.join('data', 'basketball')
TRACKING_EPOCH = '2026-03-25'

all_files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
files = [f for f in all_files if os.path.basename(f).replace('universal_predictions_','').replace('.json','') >= TRACKING_EPOCH]

u21_totals = []
for f in files:
    data = json.load(open(f, encoding='utf-8'))
    for p in data.get('predictions', []):
        if p.get('league_id') != 233:
            continue
        act_h = p.get('actual_home_score')
        act_a = p.get('actual_away_score')
        model = p.get('model_total')
        home = p.get('home_team', '')
        away = p.get('away_team', '')
        if act_h is not None and act_a is not None:
            actual = act_h + act_a
            u21_totals.append((actual, model, f"{away} @ {home}"))

u21_totals.sort(key=lambda x: x[0], reverse=True)
print(f"Espoirs U21 (League 233) — {len(u21_totals)} graded games since epoch")
print(f"{'Actual':<8} {'Model':<8} Matchup")
print("-" * 70)
for actual, model, matchup in u21_totals:
    flag = " <<" if actual > 185 else ""
    print(f"{actual:<8.0f} {model:<8.1f} {matchup}{flag}")

if u21_totals:
    avg_actual = sum(x[0] for x in u21_totals) / len(u21_totals)
    avg_model  = sum(x[1] for x in u21_totals if x[1]) / len([x for x in u21_totals if x[1]])
    print(f"\nAvg Actual Total: {avg_actual:.1f}")
    print(f"Avg Model Total:  {avg_model:.1f}")
