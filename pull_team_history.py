import json, os, glob

DATA_DIR = os.path.join('data', 'basketball')
TRACKING_EPOCH = '2026-03-25'

all_files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
files = [f for f in all_files if os.path.basename(f).replace('universal_predictions_','').replace('.json','') >= TRACKING_EPOCH]

nancy_games = []
sq_games = []
pesaro_games = []

for f in files:
    date = os.path.basename(f).replace('universal_predictions_','').replace('.json','')
    data = json.load(open(f, encoding='utf-8'))
    for p in data.get('predictions', []):
        home = p.get('home_team', '')
        away = p.get('away_team', '')
        act_h = p.get('actual_home_score')
        act_a = p.get('actual_away_score')
        model = p.get('model_total')
        vol_h = p.get('home_team_volatility')
        vol_a = p.get('away_team_volatility')
        lid = p.get('league_id')

        # Nancy U21 games (league 233)
        if lid == 233 and ('Nancy U21' in (home, away)):
            if act_h is not None and act_a is not None:
                nancy_games.append({
                    'date': date, 'home': home, 'away': away,
                    'actual': act_h + act_a, 'model': model,
                    'vol_h': vol_h, 'vol_a': vol_a
                })

        # Saint Quentin U21 games (league 233)
        if lid == 233 and ('Saint Quentin U21' in (home, away)):
            if act_h is not None and act_a is not None:
                sq_games.append({
                    'date': date, 'home': home, 'away': away,
                    'actual': act_h + act_a, 'model': model,
                    'vol_h': vol_h, 'vol_a': vol_a
                })

        # Pesaro games (league 242)
        if lid == 242 and ('Pesaro' in (home, away) or 'Rimini' in (home, away)):
            pesaro_games.append({
                'date': date, 'home': home, 'away': away,
                'actual': act_h + act_a if act_h is not None else None,
                'model': model, 'vol_h': vol_h, 'vol_a': vol_a
            })


def print_team_games(label, games):
    print(f"\n{'='*70}")
    print(f" {label} — {len(games)} graded games")
    print(f"{'='*70}")
    print(f"  {'Date':<12} {'Away':<25} {'Home':<25} {'Actual':>7} {'Model':>7} {'Max Vol':>8}")
    print(f"  {'-'*85}")
    for g in sorted(games, key=lambda x: x['date']):
        max_vol = max(g['vol_h'] or 0, g['vol_a'] or 0)
        print(f"  {g['date']:<12} {g['away']:<25} {g['home']:<25} {g['actual']:>7.0f} {g['model']:>7.1f} {max_vol:>8.2f}")
    if games:
        avg_actual = sum(g['actual'] for g in games) / len(games)
        avg_model  = sum(g['model'] for g in games if g['model']) / len([g for g in games if g['model']])
        print(f"  {'-'*85}")
        print(f"  {'AVERAGE':<38} {'':<25} {avg_actual:>7.1f} {avg_model:>7.1f}")

print_team_games("NANCY U21 (League 233)", nancy_games)
print_team_games("SAINT QUENTIN U21 (League 233)", sq_games)

# Pesaro/Rimini - show their current volatility and what score they'd get
print(f"\n{'='*70}")
print(f" PESARO vs RIMINI (League 242) - Confidence Engine Trace")
print(f"{'='*70}")
for g in pesaro_games:
    max_vol = max(g['vol_h'] or 0, g['vol_a'] or 0)
    status = "GRADED" if g['actual'] is not None else "UNGRADED"
    actual_str = f"{g['actual']:.0f}" if g['actual'] is not None else "N/A"
    print(f"  {g['date']} | {g['away']} @ {g['home']}")
    print(f"    Actual={actual_str}  Model={g['model']:.1f}  vol_h={g['vol_h']}  vol_a={g['vol_a']}  max_vol={max_vol:.2f}  [{status}]")
    print()
