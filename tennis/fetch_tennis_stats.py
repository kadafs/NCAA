"""
fetch_tennis_stats.py
=====================
Hybrid data pipeline for tennis player serve/return profiles.

Data source: Tennis-Data.co.uk (free, weekly-updated match results)
  Files: tennis/data/tennis_atp/{year}.csv  (ATP)
         tennis/data/tennis_wta/{year}w.csv  (WTA)

Profile construction:
  1. Load match CSVs → compute surface-specific win rates per player
  2. Compute implied Elo rating from win rate history
  3. Use analytical Markov inversion to derive implied serve point probability
     from Elo (i.e., find p such that simulate(p, league_avg_opp) = win_rate)
  4. Apply surface modifier from surface_engine.py
  5. Return synthetic serve profile for tennis_markov.py

Live schedule: ESPN hidden API (unauthenticated JSON)
"""

import os
import glob
import json
import math
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ATP_DIR = os.path.join(_BASE_DIR, 'data', 'tennis_atp')
_WTA_DIR = os.path.join(_BASE_DIR, 'data', 'tennis_wta')
_CACHE_DIR = os.path.join(_BASE_DIR, '..', 'data', 'tennis_cache')
os.makedirs(_CACHE_DIR, exist_ok=True)

# ============================================================
# League-average serve profiles (used as baseline / fallback)
# Calibrated so that p_server_wins_game(serve_prob) ≈ league hold rate
# ============================================================
LEAGUE_SERVE_PROFILES = {
    # ATP: ~80% hold rate → serve point prob ~0.630
    'ATP': {
        'first_serve_pct':       0.61,
        'first_serve_win_pct':   0.72,
        'second_serve_win_pct':  0.52,
        'return_points_won_pct': 0.37,
        'ace_rate':              0.07,
        'df_rate':               0.04,
        '_implied_serve_prob':   0.630,
    },
    # WTA: ~62% hold rate → serve point prob ~0.540
    'WTA': {
        'first_serve_pct':       0.59,
        'first_serve_win_pct':   0.64,
        'second_serve_win_pct':  0.47,
        'return_points_won_pct': 0.42,
        'ace_rate':              0.03,
        'df_rate':               0.05,
        '_implied_serve_prob':   0.540,
    },
}

# Elo K-factor and initial rating
ELO_K = 32
ELO_INIT = 1500


# ============================================================
# Tennis-Data.co.uk CSV Loader
# ============================================================

def _load_match_data(tour: str, min_year: int = 2019) -> pd.DataFrame:
    """Load and concatenate Tennis-Data.co.uk match files (xlsx/xls/csv)."""
    data_dir = _ATP_DIR if tour == 'ATP' else _WTA_DIR
    suffix = 'w' if tour == 'WTA' else ''

    frames = []
    for ext in ['xlsx', 'xls', 'csv']:
        pattern = os.path.join(data_dir, f'*{suffix}.{ext}')
        for f in sorted(glob.glob(pattern)):
            basename = os.path.basename(f)
            try:
                year_str = basename.replace(suffix, '').replace(f'.{ext}', '')
                year = int(year_str)
                if year < min_year:
                    continue
            except ValueError:
                continue
            try:
                if ext == 'xlsx':
                    df = pd.read_excel(f, engine='openpyxl')
                elif ext == 'xls':
                    df = pd.read_excel(f)
                else:
                    df = pd.read_csv(f, low_memory=False, encoding='latin-1')
                df['_year'] = year
                frames.append(df)
                print(f"[Tennis Data] Loaded {basename} ({len(df)} matches)")
            except Exception as e:
                print(f"[WARN] Skipping {basename}: {e}")

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    print(f"[Tennis Data] Total: {len(combined)} {tour} matches from {min_year}+")
    return combined


# ============================================================
# Elo Engine
# ============================================================

def _elo_expected(ra: float, rb: float) -> float:
    """Expected score for player A against player B in Elo."""
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def compute_elo_ratings(df: pd.DataFrame, surface_filter: str = None) -> dict:
    """
    Compute Elo ratings for all players from match history.

    Parameters
    ----------
    df             : DataFrame from _load_match_data
    surface_filter : optional 'Hard', 'Clay', 'Grass' to compute surface-specific Elo

    Returns
    -------
    dict: {player_name: elo_rating}
    """
    ratings = {}

    if df.empty:
        return ratings

    # Try to parse date column
    date_col = None
    for col in ['Date', 'date', 'tourney_date']:
        if col in df.columns:
            date_col = col
            break

    working = df.copy()
    if date_col:
        working[date_col] = pd.to_datetime(working[date_col], errors='coerce')
        working = working.sort_values(date_col)

    # Surface filter
    if surface_filter and 'Surface' in working.columns:
        working = working[working['Surface'].str.lower() == surface_filter.lower()]

    for _, row in working.iterrows():
        winner = str(row.get('Winner', row.get('winner_name', ''))).strip()
        loser = str(row.get('Loser', row.get('loser_name', ''))).strip()

        if not winner or not loser or winner == 'nan' or loser == 'nan':
            continue

        ra = ratings.get(winner, ELO_INIT)
        rb = ratings.get(loser, ELO_INIT)

        ea = _elo_expected(ra, rb)
        ratings[winner] = ra + ELO_K * (1 - ea)
        ratings[loser] = rb + ELO_K * (0 - (1 - ea))

    return ratings


def _surface_win_rate(player_name: str, df: pd.DataFrame, surface: str) -> float:
    """Compute a player's win rate on a specific surface."""
    name_lower = player_name.lower().strip()
    surf_df = df[df['Surface'].str.lower() == surface.lower()] if 'Surface' in df.columns else df

    wins = surf_df[surf_df.get('Winner', surf_df.get('winner_name', pd.Series())).str.lower().str.strip() == name_lower]
    losses = surf_df[surf_df.get('Loser', surf_df.get('loser_name', pd.Series())).str.lower().str.strip() == name_lower]

    total = len(wins) + len(losses)
    if total < 5:
        return None  # insufficient sample
    return len(wins) / total


# ============================================================
# Markov Inversion: Win Rate → Serve Point Probability
# ============================================================

def _p_server_wins_game(p: float) -> float:
    """Analytical game win probability given point win probability p."""
    p = max(0.01, min(0.99, p))
    q = 1.0 - p
    deuce = 20.0 * (p ** 3) * (q ** 3)
    win_deuce = (p ** 2) / (1.0 - 2.0 * p * q)
    return (p ** 4) + 4.0 * (p ** 4) * q + 10.0 * (p ** 4) * (q ** 2) + deuce * win_deuce


def _expected_match_win_prob(serve_p1: float, serve_p2: float,
                              sets_target: int = 2) -> float:
    """
    Estimate P(player 1 wins match) given serve point probabilities.
    Uses simplified set-level calculation (not full MC).
    """
    g1 = _p_server_wins_game(serve_p1)   # P1 holds
    g2 = _p_server_wins_game(serve_p2)   # P2 holds

    # P1 wins a service game, P2 breaks:
    p1_wins_serve_game = g1
    p1_breaks_p2 = 1.0 - g2

    # Simplified: compute P(P1 wins a set) via average of holding/breaking scenarios
    # Approximate: treat set as sequence of games with alternating serves
    # P(P1 wins set) ≈ based on relative hold rates
    hold_advantage = (p1_wins_serve_game + p1_breaks_p2) / 2.0

    # Convert to match win prob using Bradley-Terry-style formula
    if hold_advantage <= 0.5:
        p_set = max(0.01, hold_advantage)
    else:
        p_set = hold_advantage

    # Match: P(win >= sets_target sets out of <= 2*sets_target-1)
    if sets_target == 2:  # Best of 3
        return p_set ** 2 + 2 * p_set ** 2 * (1 - p_set)
    else:  # Best of 5
        q = 1 - p_set
        return (p_set ** 3 + 3 * p_set ** 3 * q +
                6 * p_set ** 3 * q ** 2)


def implied_serve_prob_from_win_rate(
    player_win_rate: float,
    tour: str,
    surface: str = 'Hard',
    tolerance: float = 0.001,
) -> float:
    """
    Invert the Markov chain: find serve point probability p such that
    the player's expected match win rate against an average opponent
    equals the observed win rate.

    Uses bisection search over p in [0.35, 0.80].

    Parameters
    ----------
    player_win_rate : observed win rate on surface (e.g. 0.68)
    tour            : 'ATP' or 'WTA'
    surface         : 'Hard', 'Clay', 'Grass'
    tolerance       : bisection convergence tolerance

    Returns
    -------
    float : implied serve point probability
    """
    from surface_engine import SURFACE_POINT_ADJUSTMENTS

    # League average opponent serve prob
    league_serve = LEAGUE_SERVE_PROFILES[tour]['_implied_serve_prob']
    sets_target = 2  # use Best-of-3 for calibration (most matches)

    lo, hi = 0.35, 0.85
    for _ in range(50):
        mid = (lo + hi) / 2.0
        # Surface adjustment applied symmetrically
        surf_adj = SURFACE_POINT_ADJUSTMENTS.get((tour, surface), 0.00)
        p_adjusted = max(0.01, min(0.99, mid + surf_adj))
        opp_adjusted = max(0.01, min(0.99, league_serve + surf_adj))

        predicted = _expected_match_win_prob(p_adjusted, opp_adjusted, sets_target)

        if abs(predicted - player_win_rate) < tolerance:
            break
        if predicted < player_win_rate:
            lo = mid
        else:
            hi = mid

    return max(0.40, min(0.75, mid))


def _serve_prob_to_profile(serve_prob: float, tour: str) -> dict:
    """
    Convert a bare serve point probability into a full serve profile
    by scaling the league-average profile proportionally.

    This allows the Markov engine to run with full profile compatibility.
    """
    league = LEAGUE_SERVE_PROFILES[tour]
    league_sp = league['_implied_serve_prob']
    scale = serve_prob / league_sp if league_sp > 0 else 1.0

    # Scale FSW% and SSW% proportionally; clamp to realistic bounds
    fsw = min(0.88, league['first_serve_win_pct'] * scale)
    ssw = min(0.72, league['second_serve_win_pct'] * scale)
    rpw = max(0.20, league['return_points_won_pct'] / scale)

    return {
        'first_serve_pct':       league['first_serve_pct'],  # stable stat
        'first_serve_win_pct':   round(fsw, 4),
        'second_serve_win_pct':  round(ssw, 4),
        'return_points_won_pct': round(rpw, 4),
        'ace_rate':              league['ace_rate'],
        'df_rate':               league['df_rate'],
        '_implied_serve_prob':   round(serve_prob, 4),
    }


# ============================================================
# Public API: Build Player Profile
# ============================================================

_elo_cache: dict = {}
_match_cache: dict = {}


def build_player_serve_profile(
    player_name: str,
    tour: str = 'ATP',
    surface: str = 'Hard',
    recent_months: int = 6,
    career_weight: float = 0.65,
) -> dict:
    """
    Build a serve/return profile for a player.

    Strategy:
      1. Load match history from Tennis-Data.co.uk CSVs
      2. Compute surface-specific win rate (career + recent blend)
      3. Invert Markov chain to get implied serve point probability
      4. Scale league-average profile to match implied serve prob
      5. Return profile dict for tennis_markov.py

    Falls back to league-average profile if insufficient data.
    """
    cache_key = f"{player_name}_{tour}_{surface}"
    cache_path = os.path.join(_CACHE_DIR, f'profile_{cache_key.replace(" ", "_")}.json')

    # 1-day cache
    if os.path.exists(cache_path):
        try:
            mtime = os.path.getmtime(cache_path)
            if (datetime.now().timestamp() - mtime) < 86400:
                with open(cache_path, encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass

    if tour not in _match_cache:
        _match_cache[tour] = _load_match_data(tour)
    df = _match_cache[tour]

    if df.empty:
        profile = LEAGUE_SERVE_PROFILES[tour].copy()
        profile['player_name'] = player_name
        profile['source'] = 'league_average_no_data'
        return profile

    # Career surface win rate
    career_wr = _surface_win_rate(player_name, df, surface)

    # Recent form win rate (last N months)
    recent_wr = None
    date_col = next((c for c in ['Date', 'date'] if c in df.columns), None)
    if date_col:
        try:
            cutoff = datetime.now() - timedelta(days=recent_months * 30)
            df_date = df.copy()
            df_date[date_col] = pd.to_datetime(df_date[date_col], errors='coerce')
            recent_df = df_date[df_date[date_col] >= cutoff]
            recent_wr = _surface_win_rate(player_name, recent_df, surface)
        except Exception:
            pass

    # Blend career + recent
    if career_wr is not None and recent_wr is not None:
        blended_wr = career_wr * career_weight + recent_wr * (1 - career_weight)
        source = 'blended'
    elif career_wr is not None:
        blended_wr = career_wr
        source = 'career_only'
    elif recent_wr is not None:
        blended_wr = recent_wr
        source = 'recent_only'
    else:
        # No data — league average
        profile = LEAGUE_SERVE_PROFILES[tour].copy()
        profile['player_name'] = player_name
        profile['source'] = 'league_average_no_matches'
        return profile

    # Invert Markov chain to get implied serve point probability
    serve_prob = implied_serve_prob_from_win_rate(blended_wr, tour, surface)
    profile = _serve_prob_to_profile(serve_prob, tour)

    profile['player_name'] = player_name
    profile['tour'] = tour
    profile['surface_filter'] = surface
    profile['observed_win_rate'] = round(blended_wr, 4)
    profile['source'] = source

    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)

    return profile


# ============================================================
# ESPN Schedule Fetcher
# ============================================================

def fetch_espn_tennis_schedule(tour: str = 'ATP') -> list:
    """
    Fetch current tennis schedule from ESPN's public API.
    Returns list of match dicts.
    """
    league_map = {'ATP': 'atp', 'WTA': 'wta'}
    league = league_map.get(tour, 'atp')
    url = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{league}/scoreboard"

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[ESPN] Failed to fetch {tour} schedule: {e}")
        return []

    matches = []
    for event in data.get('events', []):
        tournament_name = event.get('name', 'Unknown')
        for comp in event.get('competitions', []):
            competitors = comp.get('competitors', [])
            if len(competitors) < 2:
                continue
            p1 = competitors[0].get('athlete', {})
            p2 = competitors[1].get('athlete', {})
            matches.append({
                'match_id':        comp.get('id', ''),
                'p1_name':         p1.get('displayName', 'Unknown'),
                'p2_name':         p2.get('displayName', 'Unknown'),
                'tournament_name': tournament_name,
                'status':          comp.get('status', {}).get('type', {}).get('name', ''),
                'tour':            tour,
            })
    return matches


# ============================================================
# CLI Test
# ============================================================

if __name__ == '__main__':
    print("=== Testing ESPN Schedule Fetch ===")
    for t in ['ATP', 'WTA']:
        matches = fetch_espn_tennis_schedule(t)
        print(f"\n{t}: {len(matches)} matches found")
        for m in matches[:3]:
            print(f"  {m['p1_name']} vs {m['p2_name']} ({m['tournament_name']})")

    print("\n=== Testing Profile Builder ===")
    profile = build_player_serve_profile('Jannik Sinner', tour='ATP', surface='Grass')
    for k, v in profile.items():
        print(f"  {k}: {v}")
