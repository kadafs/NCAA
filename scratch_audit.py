import json, glob

TARGET = 'NBL1 CENTRAL WOMEN'

games = []
for f in sorted(glob.glob('data/basketball/universal_predictions_*.json')):
    try:
        with open(f, encoding='utf-8') as file:
            data = json.load(file)
    except:
        continue
    for p in data.get('predictions', []):
        league = p.get('league', '').upper()
        if TARGET not in league:
            continue
        if p.get('awarded_match') or p.get('actual_result') is None:
            continue
        h = p.get('actual_home_score', 0) or 0
        a = p.get('actual_away_score', 0) or 0
        actual_total = h + a
        model_total  = p.get('model_total') or p.get('final_model_total') or 0
        market       = p.get('market_total')
        signed_delta = p.get('signed_delta')  # actual - model
        decision     = p.get('decision', '?')
        arch         = p.get('model_architecture', '?').strip()
        date_str     = f[-15:-5]
        games.append({
            'date': date_str,
            'home': p.get('home_team','?'),
            'away': p.get('away_team','?'),
            'model': model_total,
            'market': market,
            'actual': actual_total,
            'signed_delta': signed_delta,
            'decision': decision,
            'arch': arch,
        })

print(f"{'Date':<12} {'Home':<28} {'Model':>6} {'Market':>7} {'Actual':>7} {'Δ (A-M)':>8}  {'Decision':<12} Arch")
print("-" * 100)
over_count = 0
under_count = 0
market_over = 0
market_total_games_with_market = 0
for g in sorted(games, key=lambda x: x['date']):
    delta_vs_model  = (g['actual'] - g['model']) if g['model'] else None
    delta_vs_market = (g['actual'] - g['market']) if g['market'] else None
    mkt_str = f"{g['market']:.1f}" if g['market'] else "  N/A"
    d_str   = f"{delta_vs_model:+.1f}" if delta_vs_model is not None else "   N/A"
    print(f"{g['date']:<12} {g['home'][:27]:<28} {g['model']:>6.1f} {mkt_str:>7} {g['actual']:>7}  {d_str:>7}  {g['decision']:<12} {g['arch']}")
    if delta_vs_model and delta_vs_model > 0:
        over_count += 1
    else:
        under_count += 1
    if delta_vs_market is not None:
        market_total_games_with_market += 1
        if delta_vs_market > 0:
            market_over += 1

print()
print(f"  Games: {len(games)} | Model overshoot (actual > model): {over_count}/{len(games)} ({100*over_count/max(len(games),1):.0f}%)")
if market_total_games_with_market:
    print(f"  Market overshoot (actual > market): {market_over}/{market_total_games_with_market} ({100*market_over/market_total_games_with_market:.0f}%) — this is the real betting signal")

# Load config for xpts_correction
try:
    with open('configs/leagues/211.json', encoding='utf-8') as f:
        cfg = json.load(f)
    print(f"\n  Config 211: avg_total={cfg.get('_avg_total')} | xpts_correction={cfg.get('_xpts_correction','none applied')}")
except Exception as e:
    print(f"  Config error: {e}")
