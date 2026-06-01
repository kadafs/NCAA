"""
global_spread_audit.py
======================
Audits the entire graded dataset (from TRACKING_EPOCH onwards) and groups
every game by its projected xpts spread band. Reports Over/Under hit rates,
game counts, and avg actual totals per band.
"""
import json
import os
import glob
import sys
from collections import defaultdict

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))
from utils.epoch_config import get_earliest_epoch, is_game_valid

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'basketball')

# ---- Spread buckets ----
BANDS = [
    ("< 2",   lambda s: s < 2),
    ("2 - 5",  lambda s: 2 <= s < 5),
    ("5 - 8",  lambda s: 5 <= s < 8),
    ("8 - 11", lambda s: 8 <= s < 11),
    ("11-15",  lambda s: 11 <= s < 15),
    ("15-20",  lambda s: 15 <= s < 20),
    ("> 20",   lambda s: s >= 20),
]

def load_valid_leagues():
    valid = set()
    lb_path = os.path.join(DATA_DIR, 'league_leaderboard.json')
    if os.path.exists(lb_path):
        with open(lb_path, 'r', encoding='utf-8') as f:
            for entry in json.load(f).get('leaderboard', []):
                adv_g = (entry.get('adv') or {}).get('graded_totals', 0)
                srs_g = (entry.get('srs') or {}).get('graded_totals', 0)
                if max(adv_g, srs_g) >= 5 and entry.get('league_id'):
                    valid.add(str(entry.get('league_id')))
    return valid

def vol_tier(h_vol, a_vol):
    """Return volatility tier label for a game."""
    avg = (h_vol + a_vol) / 2
    if h_vol < 14.8 and a_vol < 14.8:
        return "STABLE   (both < 14.8)"
    elif h_vol <= 16.6 and a_vol <= 16.6:
        return "MODERATE (both ≤ 16.6)"
    elif h_vol > 16.6 and a_vol > 16.6:
        return "VOLATILE (both > 16.6)"
    else:
        return "MIXED    (split tiers)"

def make_bucket():
    return {'total': 0, 'over_flat': 0, 'over_5': 0, 'over_10': 0,
            'actual': [], 'model': []}

def print_section(title, data):
    """Print a spread-band table for one volatility tier."""
    total_games = sum(b['total'] for b in data.values())
    if total_games == 0:
        return
    print(f"\n  --- {title}  ({total_games} games) ---")
    print(f"  {'Spread':>8}  {'Games':>6}  {'OverFlat':>9}  {'Over-5':>7}  {'Over-10':>8}  {'AvgActual':>10}  {'AvgModel':>9}  {'AvgDelta':>9}")
    print("  " + "-"*80)
    for label, _ in BANDS:
        b = data[label]
        n = b['total']
        if n == 0:
            print(f"  {label:>8}  {'0':>6}")
            continue
        avg_act   = sum(b['actual']) / n
        avg_mod   = sum(b['model'])  / n
        avg_delta = avg_act - avg_mod
        of_pct  = b['over_flat'] / n * 100
        o5_pct  = b['over_5']    / n * 100
        o10_pct = b['over_10']   / n * 100
        print(f"  {label:>8}  {n:>6}  {b['over_flat']:>4} ({of_pct:5.1f}%)  "
              f"{b['over_5']:>3} ({o5_pct:5.1f}%)  "
              f"{b['over_10']:>4} ({o10_pct:5.1f}%)  "
              f"{avg_act:>10.1f}  {avg_mod:>9.1f}  {avg_delta:>+9.1f}")

def main():
    valid_leagues = load_valid_leagues()
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
    files = [
        f for f in all_files
        if os.path.basename(f).replace('universal_predictions_', '').replace('.json', '') >= get_earliest_epoch()
    ]

    VOL_TIERS = ["STABLE   (both < 14.8)", "MODERATE (both ≤ 16.6)",
                 "MIXED    (split tiers)", "VOLATILE (both > 16.6)"]

    # tier -> band -> bucket
    data = {t: {label: make_bucket() for label, _ in BANDS} for t in VOL_TIERS}
    # combined (all tiers)
    combined = {label: make_bucket() for label, _ in BANDS}

    skipped = 0
    for pf in files:
        file_date_str = os.path.basename(pf).replace('universal_predictions_', '').replace('.json', '')
        with open(pf, 'r', encoding='utf-8') as f:
            preds = json.load(f)
        for p in preds.get('predictions', []):
            if str(p.get('league_id')) not in valid_leagues:
                continue
            if not is_game_valid(p.get('league_id'), file_date_str):
                skipped += 1; continue
            act_h      = p.get('actual_home_score')
            act_a      = p.get('actual_away_score')
            model_total = p.get('model_total')
            xpts_h     = p.get('xpts_h')
            xpts_a     = p.get('xpts_a')
            h_vol      = p.get('home_team_volatility')
            a_vol      = p.get('away_team_volatility')

            if act_h is None or act_a is None or not model_total:
                skipped += 1; continue
            if xpts_h is None or xpts_a is None or h_vol is None or a_vol is None:
                skipped += 1; continue

            spread = abs(float(xpts_h) - float(xpts_a))
            actual = float(act_h) + float(act_a)
            model  = float(model_total)
            tier   = vol_tier(float(h_vol), float(a_vol))

            for label, test in BANDS:
                if test(spread):
                    for bucket in (data[tier][label], combined[label]):
                        bucket['total']    += 1
                        bucket['actual'].append(actual)
                        bucket['model'].append(model)
                        if actual >= model:          bucket['over_flat'] += 1
                        if actual >= (model - 5):   bucket['over_5']    += 1
                        if actual >= (model - 10):  bucket['over_10']   += 1
                    break

    print()
    print("=" * 92)
    print("  GLOBAL SPREAD AUDIT — Cross-tabbed by Volatility Tier  |  Epoch:", get_earliest_epoch())
    print("=" * 92)

    print_section("ALL GAMES (combined)", combined)
    for tier in VOL_TIERS:
        print_section(tier, data[tier])

    total_games = sum(b['total'] for b in combined.values())
    print(f"\n  Files scanned: {len(files)}  |  Total graded: {total_games}  |  Skipped: {skipped}")
    print("=" * 92)

if __name__ == "__main__":
    main()
