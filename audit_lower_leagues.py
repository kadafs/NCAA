"""
audit_lower_leagues.py
----------------------------------------------------------------
Audits how well the model projected total meets or exceeds the
actual final score, specifically for LOWER and SECOND DIVISION
leagues (excluding elite_pro, top_domestic tiers, and all
Women's leagues).

Also applies the combined MAE + Volatility Green Light filter
(10%/15% of model total) to show whether stable matchups
produce significantly better hit rates.

Usage:
    python audit_lower_leagues.py
    python audit_lower_leagues.py --epoch 2026-01-01
    python audit_lower_leagues.py --min_games 5
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

DATA_DIR      = os.path.join(os.path.dirname(__file__), 'data', 'basketball')
DEFAULT_EPOCH = '2026-01-01'

LOWER_TIERS    = {'second_division', 'lower'}
EXCLUDED_TIERS = {'elite_pro', 'top_domestic', 'Telite_pro'}

# Keywords that indicate a women's league (checked against league name, case-insensitive)
WOMENS_KEYWORDS = [
    'women', ' w ', '(w)', 'lbwl', 'wbl', 'wnba', 'euroleague women',
    'euroleague-women', 'lf endesa', 'lf2', 'lf-', 'nm1 w', 'lbf w',
]

# Keywords that indicate a cup or tournament (excluded from audit)
CUP_KEYWORDS = [
    'cup', 'tournament', 'championship', 'games', 'taca', 'coppa', 'trophy',
    'afrobasket', 'eurobasket', 'america', 'asia', 'world', 'qualifier', 'olympic',
]

def is_womens_league(league_name: str) -> bool:
    name = league_name.lower().strip()
    if name.endswith(' w') or name.endswith(' women'):
        return True
    for kw in WOMENS_KEYWORDS:
        if kw in name:
            return True
    return False

def is_cup_or_tournament(league_name: str) -> bool:
    name = league_name.lower().strip()
    for kw in CUP_KEYWORDS:
        if kw in name:
            return True
    return False

# Green Light thresholds (percentage of model total)
MAE_THRESHOLD_PCT = 0.10   # combined team MAE <= 10% of model total
VOL_THRESHOLD_PCT = 0.15   # combined team Volatility <= 15% of model total

# ------------------------------------------------------------------
# Build per-team MAE and Volatility profiles from all graded history
# ------------------------------------------------------------------

def build_team_profiles(epoch):
    files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
    files = [f for f in files
             if os.path.basename(f).replace('universal_predictions_', '').replace('.json', '') >= epoch]

    team_data = defaultdict(lambda: {'errors': [], 'vols': []})

    for f in files:
        try:
            data = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        for p in data.get('predictions', []):
            act_h  = p.get('actual_home_score')
            act_a  = p.get('actual_away_score')
            xpts_h = p.get('xpts_h')
            xpts_a = p.get('xpts_a')
            h_vol  = p.get('home_team_volatility')
            a_vol  = p.get('away_team_volatility')
            home   = p.get('home_team', '')
            away   = p.get('away_team', '')

            if None not in (act_h, xpts_h) and home:
                team_data[home]['errors'].append(abs(act_h - xpts_h))
                if h_vol is not None:
                    team_data[home]['vols'].append(h_vol)

            if None not in (act_a, xpts_a) and away:
                team_data[away]['errors'].append(abs(act_a - xpts_a))
                if a_vol is not None:
                    team_data[away]['vols'].append(a_vol)

    mae_profile = {}
    vol_profile = {}
    for team, d in team_data.items():
        if d['errors']:
            mae_profile[team] = sum(d['errors']) / len(d['errors'])
        if d['vols']:
            vol_profile[team] = sum(d['vols']) / len(d['vols'])

    return mae_profile, vol_profile


# ------------------------------------------------------------------
# Load graded games (with team names for filtering)
# ------------------------------------------------------------------

def load_graded_games(epoch):
    files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
    files = [f for f in files
             if os.path.basename(f).replace('universal_predictions_', '').replace('.json', '') >= epoch]

    games = []
    for f in files:
        try:
            data = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        for p in data.get('predictions', []):
            act_h  = p.get('actual_home_score')
            act_a  = p.get('actual_away_score')
            model  = p.get('model_total')
            tier   = p.get('tier', '')
            league = p.get('league', '')
            country = p.get('country', '')
            
            if None in (act_h, act_a, model):
                continue
            if not tier:
                continue
                
            # Filters
            if country == 'USA':
                continue
            if is_womens_league(league):
                continue
            if is_cup_or_tournament(league):
                continue
                
            games.append({
                'league':    league,
                'country':   country,
                'tier':      tier,
                'home_team': p.get('home_team', ''),
                'away_team': p.get('away_team', ''),
                'actual':    act_h + act_a,
                'model':     model,
                'delta':     (act_h + act_a) - model,
            })
    return games


def apply_green_light(games, mae_profile, vol_profile):
    green, rest = [], []
    for g in games:
        model = g['model']
        home  = g['home_team']
        away  = g['away_team']

        h_mae = mae_profile.get(home)
        a_mae = mae_profile.get(away)
        h_vol = vol_profile.get(home)
        a_vol = vol_profile.get(away)

        if h_mae is None or a_mae is None:
            rest.append(g)
            continue

        combined_mae = h_mae + a_mae
        mae_passes   = combined_mae <= (model * MAE_THRESHOLD_PCT)

        if h_vol is not None and a_vol is not None:
            combined_vol = h_vol + a_vol
            vol_passes   = combined_vol <= (model * VOL_THRESHOLD_PCT)
        else:
            vol_passes = True  # no data — don't penalise

        if mae_passes and vol_passes:
            green.append(g)
        else:
            rest.append(g)

    return green, rest


def compute_stats(records):
    if not records:
        return None
    n          = len(records)
    deltas     = [r['delta'] for r in records]
    avg_delta  = sum(deltas) / n
    flat_hits  = sum(1 for d in deltas if d >= 0)
    c5_hits    = sum(1 for d in deltas if d >= -5)
    c10_hits   = sum(1 for d in deltas if d >= -10)
    overs      = sum(1 for d in deltas if d > 0)
    unders     = sum(1 for d in deltas if d < 0)
    return {
        'n':         n,
        'avg_delta': round(avg_delta, 1),
        'flat_pct':  round(flat_hits / n * 100, 1),
        'c5_pct':    round(c5_hits   / n * 100, 1),
        'c10_pct':   round(c10_hits  / n * 100, 1),
        'over_pct':  round(overs     / n * 100, 1),
        'under_pct': round(unders    / n * 100, 1),
    }


def print_stats_row(label, s, width=44):
    if not s:
        print(f'  {label:<{width}} | {"N/A":>5}')
        return
    delta_str = f'{s["avg_delta"]:+.1f}'
    direction = 'OVER ' if s['avg_delta'] > 0 else 'UNDER'
    print(
        f'  {label:<{width}} | {s["n"]:>5} | '
        f'{s["flat_pct"]:>6}% | '
        f'{s["c5_pct"]:>6}% | '
        f'{s["c10_pct"]:>6}% | '
        f'{delta_str:>6} ({direction}) | '
        f'{s["over_pct"]:>5}% O  {s["under_pct"]:>5}% U'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epoch',     default=DEFAULT_EPOCH)
    parser.add_argument('--min_games', type=int, default=5)
    args = parser.parse_args()

    col = 44
    SEP = '  ' + '-' * 114
    EQ  = '  ' + '=' * 114
    HDR = (
        f'  {"Segment":<{col}} | {"Games":>5} | '
        f'{"Flat%":>6} | {"-5%":>6} | {"-10%":>6} | '
        f'{"Avg Delta":>13} | {"Over/Under":>20}'
    )

    print()
    print(EQ)
    print('  LOWER LEAGUE AUDIT (Men Only) + Green Light Filter')
    print(f'  Epoch: {args.epoch}  |  MAE <= {MAE_THRESHOLD_PCT*100:.0f}%  |  Vol <= {VOL_THRESHOLD_PCT*100:.0f}%  of Model Total')
    print(EQ)

    print('\n  Building team profiles...')
    mae_profile, vol_profile = build_team_profiles(args.epoch)
    print(f'  {len(mae_profile)} teams with MAE data  |  {len(vol_profile)} teams with Volatility data')

    all_games   = load_graded_games(args.epoch)
    top_games   = [g for g in all_games if g['tier'] in EXCLUDED_TIERS]
    lower_games = [g for g in all_games if g['tier'] in LOWER_TIERS]

    lower_green, lower_rest = apply_green_light(lower_games, mae_profile, vol_profile)
    top_green,   top_rest   = apply_green_light(top_games,   mae_profile, vol_profile)

    print(f'\n  Games loaded (men only): {len(all_games)}')
    print(f'  Top division: {len(top_games)}  ->  {len(top_green)} Green Light')
    print(f'  Lower leagues: {len(lower_games)}  ->  {len(lower_green)} Green Light')

    # ── MAIN COMPARISON TABLE ─────────────────────────────────
    print()
    print(EQ)
    print('  UNFILTERED vs GREEN LIGHT FILTER')
    print(EQ)
    print(HDR)
    print(SEP)
    print_stats_row('TOP DIV  — All Games',        compute_stats(top_games),   width=col)
    print_stats_row('TOP DIV  — Green Light Only', compute_stats(top_green),   width=col)
    print(SEP)
    print_stats_row('LOWER    — All Games',        compute_stats(lower_games), width=col)
    print_stats_row('LOWER    — Green Light Only', compute_stats(lower_green), width=col)
    print(EQ)

    # ── PER-LEAGUE BREAKDOWN ──────────────────────────────────
    print(f'\n  PER-LEAGUE (min {args.min_games} games, sorted by All-games -10%):')
    print()
    print(HDR)
    print(SEP)

    by_league       = defaultdict(list)
    by_league_green = defaultdict(list)
    for g in lower_games:
        by_league[f"{g['country']} - {g['league']}"].append(g)
    for g in lower_green:
        by_league_green[f"{g['country']} - {g['league']}"].append(g)

    rows = []
    for key, records in by_league.items():
        if len(records) < args.min_games:
            continue
        s_all   = compute_stats(records)
        s_green = compute_stats(by_league_green.get(key, []))
        tier    = records[0]['tier']
        rows.append((key, tier, s_all, s_green))

    rows.sort(key=lambda x: x[2]['c10_pct'], reverse=True)

    for key, tier, s_all, s_green in rows:
        tier_tag = f'[{tier[:4].upper()}]'
        print_stats_row(f'{tier_tag} {key}  (all)',    s_all,   width=col)
        if s_green:
            n_g = s_green['n']
            print_stats_row(f'  -> Green Light ({n_g}g)', s_green, width=col)
        else:
            print(f'  {"  -> Green Light":>{col+2}}  (no qualifying games)')
        print()

    # ── VERDICT ───────────────────────────────────────────────
    s_la = compute_stats(lower_games)
    s_lg = compute_stats(lower_green)
    if s_la and s_lg:
        print(EQ)
        print('  GREEN LIGHT LIFT (Lower Leagues):')
        lf = s_lg['flat_pct'] - s_la['flat_pct']
        lc = s_lg['c10_pct']  - s_la['c10_pct']
        print(f'    Flat Floor : {s_la["flat_pct"]}%  ->  {s_lg["flat_pct"]}%   ({lf:+.1f} pp)')
        print(f'    -10 Cushion: {s_la["c10_pct"]}%  ->  {s_lg["c10_pct"]}%   ({lc:+.1f} pp)')
        print(f'    Avg Delta  : {s_la["avg_delta"]:+.1f}  ->  {s_lg["avg_delta"]:+.1f}')
        print(EQ)
    print()


if __name__ == '__main__':
    main()
