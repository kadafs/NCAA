"""
audit_xpts_spread.py
--------------------------------------------------------------
Two-part analysis of how xPTS spread between teams affects
prediction quality.

  PART 1 - MONEYLINE WIN RATE
    How often does the team with the higher xPTS actually win?

  PART 2 - MODEL SCORE MEET / EXCEED RATE
    How often does the actual combined score meet or exceed the
    model's predicted total (flat floor)?
    Also shown at -5 / -10 cushion thresholds.

Spread bands (user-requested):
    1-5     Close
    6-11    Moderate
    >=12    Blowout
    <1      Pick-Em (bonus band)

Usage:
    python audit_xpts_spread.py
    python audit_xpts_spread.py --epoch 2026-03-25
    python audit_xpts_spread.py --league "Spain"
"""

import sys
import json
import glob
import os
import argparse
from collections import defaultdict

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'basketball')
DEFAULT_EPOCH = '2026-03-25'

# -- Spread band definitions ----------------------------------
BANDS = [
    ('< 1  (Pick-Em)',   lambda s: s < 1),
    ('1-5  (Close)',     lambda s: 1 <= s <= 5.99),
    ('6-11 (Moderate)', lambda s: 6 <= s <= 11.99),
    ('>= 12 (Blowout)', lambda s: s >= 12),
]

def get_band(spread: float) -> str:
    for label, fn in BANDS:
        if fn(spread):
            return label
    return '>= 12 (Blowout)'


def empty_bin():
    return {
        # Part 1 - Win rate
        'games':       0,
        'ml_wins':     0,  # predicted winner == actual winner

        # Part 2 - Score meet/exceed
        'scored_games': 0,   # games with both xpts AND model_total AND actuals
        'meet_flat':    0,   # actual_total >= model_total
        'meet_5':       0,   # actual_total >= model_total - 5
        'meet_10':      0,   # actual_total >= model_total - 10

        # Score difference details (for context)
        'delta_sum':    0.0,
        'over_count':   0,   # actual_total > model_total
        'under_count':  0,   # actual_total < model_total
        'exact_count':  0,   # actual_total == model_total
    }


def run_audit(epoch: str = DEFAULT_EPOCH, league_filter: str = ''):
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
    files = [
        f for f in all_files
        if os.path.basename(f).replace('universal_predictions_', '').replace('.json', '') >= epoch
    ]

    if not files:
        print(f"[!] No prediction files found on or after {epoch}")
        return

    bins     = {label: empty_bin() for label, _ in BANDS}
    totals   = empty_bin()

    skipped_no_xpts   = 0
    skipped_ungraded  = 0
    skipped_filter    = 0
    skipped_tie       = 0

    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            continue

        for p in data.get('predictions', []):
            # Optional league/team filter
            if league_filter:
                lf = league_filter.lower()
                league_str = f"{p.get('country','')} - {p.get('league','')}".lower()
                home_str   = p.get('home_team', '').lower()
                away_str   = p.get('away_team', '').lower()
                if lf not in league_str and lf not in home_str and lf not in away_str:
                    skipped_filter += 1
                    continue

            act_h = p.get('actual_home_score')
            act_a = p.get('actual_away_score')

            if act_h is None or act_a is None:
                skipped_ungraded += 1
                continue

            xpts_h = p.get('xpts_h')
            xpts_a = p.get('xpts_a')

            if xpts_h is None or xpts_a is None:
                skipped_no_xpts += 1
                continue

            # Skip ties in actual score (extremely rare in basketball)
            if act_h == act_a:
                skipped_tie += 1
                continue

            spread = abs(xpts_h - xpts_a)
            band   = get_band(spread)

            # -- Part 1: Moneyline win rate --
            pred_home_wins   = xpts_h > xpts_a
            actual_home_wins = act_h  > act_a
            ml_correct       = (pred_home_wins == actual_home_wins)

            bins[band]['games']   += 1
            totals['games']       += 1
            if ml_correct:
                bins[band]['ml_wins'] += 1
                totals['ml_wins']     += 1

            # -- Part 2: Model score meet/exceed --
            model_total = p.get('model_total') or (p.get('model') or {}).get('total')
            if model_total:
                actual_total = act_h + act_a
                signed_delta = actual_total - model_total

                bins[band]['scored_games'] += 1
                totals['scored_games']     += 1
                bins[band]['delta_sum']    += signed_delta
                totals['delta_sum']        += signed_delta

                if actual_total >= model_total:
                    bins[band]['meet_flat']  += 1
                    bins[band]['over_count'] += (1 if actual_total > model_total else 0)
                    bins[band]['exact_count']+= (1 if actual_total == model_total else 0)
                    totals['meet_flat']      += 1
                    totals['over_count']     += (1 if actual_total > model_total else 0)
                    totals['exact_count']    += (1 if actual_total == model_total else 0)
                else:
                    bins[band]['under_count'] += 1
                    totals['under_count']     += 1

                if actual_total >= model_total - 5:
                    bins[band]['meet_5']  += 1
                    totals['meet_5']      += 1

                if actual_total >= model_total - 10:
                    bins[band]['meet_10'] += 1
                    totals['meet_10']     += 1

    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------
    W = 110
    print()
    print("=" * W)
    print("   xPTS SPREAD ANALYSIS  -  WIN RATE  &  SCORE MEET / EXCEED RATE")
    if league_filter:
        print(f"   Filter: '{league_filter.upper()}'")
    print(f"   Files scanned: {len(files)}  |  Epoch: {epoch}")
    print("=" * W)

    # -- PART 1 ----------------------------------------------
    print()
    print("  PART 1 - MONEYLINE WIN RATE")
    print("  How often does the team with the higher xPTS actually win the game?")
    print()
    print(f"  {'xPTS Spread Band':<22} | {'Games':>7} | {'Correct':>8} | {'Win Rate':>9}")
    print("  " + "-" * 57)

    band_order = [label for label, _ in BANDS]
    for label in band_order:
        v = bins[label]
        g = v['games']
        if g > 0:
            rate = v['ml_wins'] / g * 100
            print(f"  {label:<22} | {g:>7} | {v['ml_wins']:>8} | {rate:>8.1f}%")
        else:
            print(f"  {label:<22} | {g:>7} | {'-':>8} | {'-':>9}")

    print("  " + "-" * 57)
    tg = totals['games']
    if tg > 0:
        overall_rate = totals['ml_wins'] / tg * 100
        print(f"  {'OVERALL':<22} | {tg:>7} | {totals['ml_wins']:>8} | {overall_rate:>8.1f}%")
    print()
    print("  Note: Win Rate = how often the xPTS favourite actually won the game.")

    # -- PART 2 ----------------------------------------------
    print()
    print("=" * W)
    print()
    print("  PART 2 - MODEL SCORE MEET / EXCEED RATE")
    print("  How often does the actual combined total meet or exceed the model's predicted total?")
    print("  Columns: Flat Floor (actual >= model) | Cushion-5 (actual >= model-5) | Cushion-10 (actual >= model-10)")
    print()

    hdr = (f"  {'xPTS Spread Band':<22} | {'Games':>7} | {'Scored':>7}"
           f" | {'Flat >=':>10} | {'Cushion -5':>12} | {'Cushion -10':>13}"
           f" | {'Avg Delta':>10}")
    print(hdr)
    print("  " + "-" * 95)

    for label in band_order:
        v  = bins[label]
        g  = v['games']
        sg = v['scored_games']

        if sg > 0:
            pct_flat = v['meet_flat'] / sg * 100
            pct_5    = v['meet_5']    / sg * 100
            pct_10   = v['meet_10']   / sg * 100
            avg_d    = v['delta_sum'] / sg

            flat_str = f"{v['meet_flat']}/{sg} ({pct_flat:.0f}%)"
            str_5    = f"{v['meet_5']}/{sg} ({pct_5:.0f}%)"
            str_10   = f"{v['meet_10']}/{sg} ({pct_10:.0f}%)"
            delta_str = f"{avg_d:+.1f}pts"

            print(f"  {label:<22} | {g:>7} | {sg:>7} | {flat_str:>12} | {str_5:>14} | {str_10:>14} | {delta_str:>9}")
        else:
            print(f"  {label:<22} | {g:>7} | {0:>7} | {'-':>12} | {'-':>14} | {'-':>14} | {'-':>9}")

    print("  " + "-" * 95)

    sg_tot = totals['scored_games']
    if sg_tot > 0:
        pct_flat = totals['meet_flat'] / sg_tot * 100
        pct_5    = totals['meet_5']    / sg_tot * 100
        pct_10   = totals['meet_10']   / sg_tot * 100
        avg_d    = totals['delta_sum'] / sg_tot

        flat_str = f"{totals['meet_flat']}/{sg_tot} ({pct_flat:.0f}%)"
        str_5    = f"{totals['meet_5']}/{sg_tot} ({pct_5:.0f}%)"
        str_10   = f"{totals['meet_10']}/{sg_tot} ({pct_10:.0f}%)"
        delta_str = f"{avg_d:+.1f}pts"
        print(f"  {'OVERALL':<22} | {tg:>7} | {sg_tot:>7} | {flat_str:>12} | {str_5:>14} | {str_10:>14} | {delta_str:>9}")

    print()
    print("  Avg Delta = average of (actual_total - model_total). Negative = model over-predicted.")

    # -- PART 3: Over/Under breakdown ------------------------
    print()
    print("=" * W)
    print()
    print("  PART 3 - SCORING DIRECTION BY SPREAD BAND")
    print("  Of scored games: how many ran OVER, EXACT, or UNDER the model total?")
    print()
    print(f"  {'xPTS Spread Band':<22} | {'Scored':>7} | {'OVER':>10} | {'EXACT':>8} | {'UNDER':>10}")
    print("  " + "-" * 66)

    for label in band_order:
        v  = bins[label]
        sg = v['scored_games']
        if sg > 0:
            over_pct  = v['over_count']  / sg * 100
            exact_pct = v['exact_count'] / sg * 100
            under_pct = v['under_count'] / sg * 100
            print(f"  {label:<22} | {sg:>7} | {v['over_count']:>4} ({over_pct:4.0f}%) | {v['exact_count']:>4} ({exact_pct:3.0f}%) | {v['under_count']:>4} ({under_pct:4.0f}%)")
        else:
            print(f"  {label:<22} | {0:>7} | {'-':>10} | {'-':>8} | {'-':>10}")

    print("  " + "-" * 66)
    if sg_tot > 0:
        over_pct  = totals['over_count']  / sg_tot * 100
        exact_pct = totals['exact_count'] / sg_tot * 100
        under_pct = totals['under_count'] / sg_tot * 100
        print(f"  {'OVERALL':<22} | {sg_tot:>7} | {totals['over_count']:>4} ({over_pct:4.0f}%) | {totals['exact_count']:>4} ({exact_pct:3.0f}%) | {totals['under_count']:>4} ({under_pct:4.0f}%)")

    print()
    print(f"  Skipped - ungraded: {skipped_ungraded} | no xPTS: {skipped_no_xpts}"
          f" | actual tie: {skipped_tie} | filtered out: {skipped_filter}")
    print("=" * W)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Audit xPTS spread vs win rate and model score accuracy."
    )
    parser.add_argument('--epoch',  default=DEFAULT_EPOCH,
                        help=f'Start date (YYYY-MM-DD). Default: {DEFAULT_EPOCH}')
    parser.add_argument('--league', default='',
                        help='Optional: filter by league/country/team substring')
    args = parser.parse_args()
    run_audit(epoch=args.epoch, league_filter=args.league)


if __name__ == '__main__':
    main()
