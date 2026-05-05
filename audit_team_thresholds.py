"""
audit_team_thresholds.py
----------------------------------------------------------------
Audits per-team Scoring Volatility and MAE from graded history
to recommend realistic GREEN LIGHT thresholds.

For each team seen in graded games:
  - MAE    = mean(|xpts_team - actual_team_score|)
  - Bias   = mean(actual_team_score - xpts_team)
  - Vol    = std_dev_totals from their stats file (if found)

Usage:
    python audit_team_thresholds.py
    python audit_team_thresholds.py --epoch 2026-03-25
    python audit_team_thresholds.py --min_games 5
"""

import sys
import json
import glob
import os
import math
import argparse
from collections import defaultdict

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_DIR     = os.path.join(os.path.dirname(__file__), 'data', 'basketball')
DEFAULT_EPOCH = '2026-03-25'


# ------------------------------------------------------------------
# 1. Build per-team MAE/Bias from graded prediction files
# ------------------------------------------------------------------

def build_team_records(epoch, min_games):
    files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
    files = [
        f for f in files
        if os.path.basename(f).replace('universal_predictions_', '').replace('.json', '') >= epoch
    ]

    # team_key -> list of (xpts, actual)
    records = defaultdict(list)   # key = (league_id, team_name)

    for f in files:
        try:
            data = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue

        for p in data.get('predictions', []):
            act_h = p.get('actual_home_score')
            act_a = p.get('actual_away_score')
            xpts_h = p.get('xpts_h')
            xpts_a = p.get('xpts_a')

            # Only graded + both xpts present
            if None in (act_h, act_a, xpts_h, xpts_a):
                continue

            lid = p.get('league_id')
            home = p.get('home_team', '')
            away = p.get('away_team', '')

            records[(lid, home)].append((xpts_h, act_h))
            records[(lid, away)].append((xpts_a, act_a))

    # Collapse into stats
    team_stats = []
    for (lid, name), pairs in records.items():
        if len(pairs) < min_games:
            continue
        errors  = [abs(xp - ac) for xp, ac in pairs]
        deltas  = [ac - xp    for xp, ac in pairs]
        mae     = sum(errors) / len(errors)
        bias    = sum(deltas) / len(deltas)
        team_stats.append({
            'league_id': lid,
            'name':      name,
            'games':     len(pairs),
            'mae':       round(mae,  2),
            'bias':      round(bias, 2),
        })

    return team_stats


# ------------------------------------------------------------------
# 2. Attach volatility from stats files
# ------------------------------------------------------------------

def attach_volatility(team_stats):
    # Load ALL adv + srs stats files into one lookup: team_name_lower -> std_dev_totals
    vol_lookup = {}
    for pattern in ('data/bball_stats_*_adv.json', 'data/bball_stats_*_srs.json'):
        for f in glob.glob(pattern):
            try:
                data = json.load(open(f, encoding='utf-8'))
                for t in data.get('teams', []):
                    key  = t.get('team_name', '').lower().strip()
                    vol  = t.get('std_dev_totals')
                    if key and vol is not None:
                        vol_lookup[key] = vol
            except Exception:
                pass

    for t in team_stats:
        key = t['name'].lower().strip()
        t['vol'] = vol_lookup.get(key)   # None if not found

    return team_stats


# ------------------------------------------------------------------
# 3. Percentile helper
# ------------------------------------------------------------------

def percentile(data, pct):
    if not data:
        return None
    s = sorted(data)
    idx = (pct / 100) * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return round(s[lo] + (idx - lo) * (s[hi] - s[lo]), 2)


# ------------------------------------------------------------------
# 4. Main audit
# ------------------------------------------------------------------

def run_audit(epoch, min_games):
    print()
    print('=' * 80)
    print('  TEAM-LEVEL THRESHOLD AUDIT')
    print(f'  Epoch: {epoch}  |  Min games per team: {min_games}')
    print('=' * 80)

    print('\n  [1/3] Building team records from graded history...')
    team_stats = build_team_records(epoch, min_games)

    if not team_stats:
        print('  [!] No team data found. Check epoch or min_games.')
        return

    print(f'  Found {len(team_stats)} teams with >= {min_games} graded games.\n')

    print('  [2/3] Attaching volatility from stats files...')
    team_stats = attach_volatility(team_stats)

    # Split into those with/without volatility data
    with_vol    = [t for t in team_stats if t['vol'] is not None]
    without_vol = [t for t in team_stats if t['vol'] is None]
    print(f'  Volatility matched: {len(with_vol)} teams  |  Unmatched: {len(without_vol)} teams\n')

    print('  [3/3] Computing distributions...')

    mae_vals = [t['mae'] for t in team_stats]
    vol_vals = [t['vol'] for t in with_vol]
    bias_vals = [t['bias'] for t in team_stats]

    # ── MAE Distribution ─────────────────────────────────────
    print()
    print('  =' * 40)
    print('  TEAM MAE DISTRIBUTION  (|xpts_team - actual_team_score|)')
    print('  -' * 40)
    pcts = [10, 20, 25, 33, 40, 50, 60, 67, 75, 80, 90]
    print(f'  {"Percentile":<14} | {"MAE Value":>10}  |  Interpretation')
    print(f'  {"-"*60}')
    for p in pcts:
        v = percentile(mae_vals, p)
        note = ''
        if p <= 25:  note = '<-- Excellent (best teams)'
        elif p <= 50: note = '<-- Good'
        elif p <= 75: note = '<-- Average'
        else:         note = '<-- Noisy / unreliable'
        print(f'  P{p:<13} | {v:>10.2f}  |  {note}')

    print(f'\n  Min MAE  : {min(mae_vals):.2f}')
    print(f'  Max MAE  : {max(mae_vals):.2f}')
    print(f'  Avg MAE  : {sum(mae_vals)/len(mae_vals):.2f}')

    # Bucket breakdown for MAE
    print()
    print(f'  {"MAE Bucket":<18} | {"Teams":>6} | {"% of Total":>10}')
    print(f'  {"-"*40}')
    buckets = [(0,5), (5,8), (8,10), (10,12), (12,15), (15,999)]
    labels  = ['0-5 (Elite)', '5-8 (Good)', '8-10 (OK)', '10-12 (Moderate)', '12-15 (Poor)', '15+ (Unreliable)']
    for (lo, hi), label in zip(buckets, labels):
        count = sum(1 for v in mae_vals if lo <= v < hi)
        pct   = count / len(mae_vals) * 100
        bar   = '#' * int(pct / 2)
        print(f'  {label:<18} | {count:>6} | {pct:>8.1f}%  {bar}')

    # ── Volatility Distribution ──────────────────────────────
    if vol_vals:
        print()
        print('  =' * 40)
        print('  TEAM SCORING VOLATILITY DISTRIBUTION  (std_dev_totals)')
        print('  -' * 40)
        print(f'  {"Percentile":<14} | {"Vol Value":>10}  |  Interpretation')
        print(f'  {"-"*60}')
        for p in pcts:
            v = percentile(vol_vals, p)
            note = ''
            if p <= 25:  note = '<-- Stable / predictable'
            elif p <= 50: note = '<-- Average'
            elif p <= 75: note = '<-- Somewhat volatile'
            else:         note = '<-- Highly unpredictable'
            print(f'  P{p:<13} | {v:>10.2f}  |  {note}')

        print(f'\n  Min Vol  : {min(vol_vals):.2f}')
        print(f'  Max Vol  : {max(vol_vals):.2f}')
        print(f'  Avg Vol  : {sum(vol_vals)/len(vol_vals):.2f}')

        print()
        print(f'  {"Vol Bucket":<18} | {"Teams":>6} | {"% of Total":>10}')
        print(f'  {"-"*40}')
        vbuckets = [(0,10), (10,13), (13,15), (15,17), (17,20), (20,999)]
        vlabels  = ['0-10 (Rock Solid)', '10-13 (Stable)', '13-15 (Normal)', '15-17 (Volatile)', '17-20 (High Vol)', '20+ (Extreme)']
        for (lo, hi), label in zip(vbuckets, vlabels):
            count = sum(1 for v in vol_vals if lo <= v < hi)
            pct   = count / len(vol_vals) * 100
            bar   = '#' * int(pct / 2)
            print(f'  {label:<18} | {count:>6} | {pct:>8.1f}%  {bar}')

    # ── GREEN LIGHT Recommendations ──────────────────────────
    print()
    print('  =' * 40)
    print('  GREEN LIGHT THRESHOLD RECOMMENDATIONS')
    print('  -' * 40)

    mae_p25  = percentile(mae_vals, 25)
    mae_p33  = percentile(mae_vals, 33)
    mae_p50  = percentile(mae_vals, 50)

    vol_p25  = percentile(vol_vals, 25) if vol_vals else None
    vol_p33  = percentile(vol_vals, 33) if vol_vals else None
    vol_p50  = percentile(vol_vals, 50) if vol_vals else None

    # Count eligible teams at each threshold combo
    def count_eligible(mae_thr, vol_thr):
        eligible = 0
        for t in team_stats:
            if t['mae'] <= mae_thr:
                if vol_thr is None or t['vol'] is None or t['vol'] <= vol_thr:
                    eligible += 1
        return eligible

    print()
    print(f'  Your original ideals: Vol <= 14-15 | MAE <= 8-10')
    print(f'  Reality check from your actual data:\n')

    tiers = [
        ('STRICT (Top 25%)',    mae_p25, vol_p25),
        ('BALANCED (Top 33%)', mae_p33, vol_p33),
        ('LOOSE (Median)',      mae_p50, vol_p50),
    ]

    for label, mae_t, vol_t in tiers:
        n = count_eligible(mae_t, vol_t)
        pct = n / len(team_stats) * 100
        vol_str = f'{vol_t:.1f}' if vol_t else 'N/A'
        print(f'  [{label}]')
        print(f'    MAE <= {mae_t:.1f}  |  Vol <= {vol_str}')
        print(f'    Eligible teams: {n}/{len(team_stats)} ({pct:.1f}%)')
        print()

    # ── Top 20 most predictable teams ───────────────────────
    print('  =' * 40)
    print('  TOP 20 MOST PREDICTABLE TEAMS  (lowest MAE, min 5 games)')
    print('  -' * 40)
    print(f'  {"Team":<30} | {"Games":>5} | {"MAE":>6} | {"Bias":>7} | {"Vol":>6}')
    print(f'  {"-"*65}')

    top20 = sorted(team_stats, key=lambda x: x['mae'])[:20]
    for t in top20:
        vol_str = f'{t["vol"]:.1f}' if t['vol'] is not None else ' N/A'
        print(f'  {t["name"]:<30} | {t["games"]:>5} | {t["mae"]:>6.2f} | {t["bias"]:>+7.2f} | {vol_str:>6}')

    # ── Worst 20 teams ───────────────────────────────────────
    print()
    print('  BOTTOM 20 MOST UNPREDICTABLE TEAMS  (highest MAE)')
    print(f'  {"-"*65}')
    bottom20 = sorted(team_stats, key=lambda x: x['mae'], reverse=True)[:20]
    for t in bottom20:
        vol_str = f'{t["vol"]:.1f}' if t['vol'] is not None else ' N/A'
        print(f'  {t["name"]:<30} | {t["games"]:>5} | {t["mae"]:>6.2f} | {t["bias"]:>+7.2f} | {vol_str:>6}')

    print()
    print('  =' * 80)
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epoch',     default=DEFAULT_EPOCH)
    parser.add_argument('--min_games', type=int, default=5)
    args = parser.parse_args()
    run_audit(epoch=args.epoch, min_games=args.min_games)


if __name__ == '__main__':
    main()
