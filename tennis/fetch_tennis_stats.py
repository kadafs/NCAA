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
import re
import glob
import json
import unicodedata
import difflib
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
    # ATP: ~80% hold rate -> _p_server_wins_game(0.633) = 0.8002
    'ATP': {
        'first_serve_pct':       0.61,
        'first_serve_win_pct':   0.72,
        'second_serve_win_pct':  0.52,
        'return_points_won_pct': 0.37,
        'ace_rate':              0.07,
        'df_rate':               0.04,
        '_implied_serve_prob':   0.633,   # Bug 3 fix: was 0.630 -> gave 0.795 hold
    },
    # WTA: ~62% hold rate -> _p_server_wins_game(0.549) = 0.6208
    'WTA': {
        'first_serve_pct':       0.59,
        'first_serve_win_pct':   0.64,
        'second_serve_win_pct':  0.47,
        'return_points_won_pct': 0.42,
        'ace_rate':              0.03,
        'df_rate':               0.05,
        '_implied_serve_prob':   0.549,   # Bug 3 fix: was 0.540 -> gave 0.599 hold
    },
}

# Elo K-factor and initial rating
ELO_K = 32
ELO_INIT = 1500


# ============================================================
# Retirement / Walkover markers in Tennis-Data.co.uk Comment column
# ============================================================
_INCOMPLETE_PATTERNS = re.compile(
    r'(?:retired|ret\.?|walkover|w/o|abandoned|def\.|default)',
    re.IGNORECASE
)

# Retirement tracking: populated by _load_match_data
_retirement_counts: dict = {}   # player_key -> count of retirement-involved matches
_match_counts:      dict = {}   # player_key -> total matches


def _load_match_data(tour: str, min_year: int = 2019) -> pd.DataFrame:
    """
    Load and concatenate Tennis-Data.co.uk match files (xlsx/xls/csv).

    Fix 1 – Retirement Yield Leak:
      Rows where the 'Comment' column contains 'Retired' or 'Walkover'
      are quarantined (never used for win-rate calculations).
      A side-channel _retirement_counts dict tracks how often each
      player appears in a retirement so consensus_tennis.py can
      flag injury-prone matchups with a safety-void.
    """
    global _retirement_counts, _match_counts
    _retirement_counts = {}
    _match_counts = {}

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

    # --- Bug 2 + Fix 1: Quarantine incomplete matches, single-pass count ---
    comment_col = next((c for c in combined.columns if c.strip().lower() == 'comment'), None)
    if comment_col:

        is_incomplete = combined[comment_col].astype(str).str.contains(
            _INCOMPLETE_PATTERNS, regex=True, na=False
        )
        ret_df = combined[is_incomplete]

        # Bug 2 fix: single combined pass prevents multi-call over-count.
        # Both retirement and total counts accumulated in one iteration.
        for col in ['Winner', 'Loser']:
            if col in ret_df.columns:
                for r_name in ret_df[col].dropna().astype(str):
                    k = normalize_tennis_name(r_name)
                    _retirement_counts[k] = _retirement_counts.get(k, 0) + 1
            if col in combined.columns:
                for r_name in combined[col].dropna().astype(str):
                    k = normalize_tennis_name(r_name)
                    _match_counts[k] = _match_counts.get(k, 0) + 1

        n_removed = is_incomplete.sum()
        if n_removed:
            print(f"[Tennis Data] Quarantined {n_removed} retired/walkover rows "
                  f"({n_removed/len(combined)*100:.1f}%)")
        combined = combined[~is_incomplete].copy()

    print(f"[Tennis Data] Total: {len(combined)} {tour} completed matches from {min_year}+")
    return combined


# ============================================================
# Name Normalization (Fix 2: Multi-Surface Name Normalization Trap)
# ============================================================

# Static alias map for common Tennis-Data.co.uk spelling variations
# and cross-source mismatches. Maps raw variants -> canonical key.
# Format: all lowercase, no accents, "surname-initial"
TOP_50_ALIASES: dict[str, str] = {
    # ATP
    'berrettini-m':   'berrettini-m',   # canonical
    'm.berrettini':   'berrettini-m',
    'de minaur-a':    'de minaur-a',
    'deminaur-a':     'de minaur-a',
    'de minaur a':    'de minaur-a',
    'del potro-j':    'del potro-j',
    'delpotro-j':     'del potro-j',
    'van de zandschulp-b': 'van de zandschulp-b',
    'van rijthoven-t': 'van rijthoven-t',
    'tsitsipas-s':    'tsitsipas-s',
    'dimitrov-g':     'dimitrov-g',
    'khachanov-k':    'khachanov-k',
    'rublev-a':       'rublev-a',
    'medvedev-d':     'medvedev-d',
    'zverev-a':       'zverev-a',
    'alcaraz-c':      'alcaraz-c',
    'sinner-j':       'sinner-j',
    'djokovic-n':     'djokovic-n',
    'nadal-r':        'nadal-r',
    'federer-r':      'federer-r',
    # WTA
    'swiatek-i':      'swiatek-i',
    'sabalenka-a':    'sabalenka-a',
    'gauff-c':        'gauff-c',
    'rybakina-e':     'rybakina-e',
    'krejcikova-b':   'krejcikova-b',
    'kvitova-p':      'kvitova-p',
    'halep-s':        'halep-s',
    'wozniacki-c':    'wozniacki-c',
    'kontaveit-a':    'kontaveit-a',
    'pliskova-k':     'pliskova-k',
    'badosa-p':       'badosa-p',
    'pegula-j':       'pegula-j',
    'jabeur-o':       'jabeur-o',
    'vondrousova-m':  'vondrousova-m',
    'andreescu-b':    'andreescu-b',
    'kerber-a':       'kerber-a',
    'azarenka-v':     'azarenka-v',
    'muguruza-g':     'muguruza-g',
}


def normalize_tennis_name(name_str: str) -> str:
    """
    Transforms player names into a canonical lowercase 'lastname-initial'
    anchor that is immune to:
      - Accent characters  (Alcaráz -> alcaraz)
      - Dot / comma noise  (M.Berrettini -> berrettini-m)
      - Case differences   (SINNER -> sinner)
      - Trailing whitespace

    Returns the canonical key: e.g., 'sinner-j', 'alcaraz-c', 'swiatek-i'.
    Checks TOP_50_ALIASES first for hardcoded exception overrides.
    Falls back to automatic parsing for all other names.
    """
    if not name_str or str(name_str).strip().lower() in ('nan', '', 'unknown'):
        return 'unknown'

    # 1. Strip accents via Unicode NFD decomposition
    nfd = unicodedata.normalize('NFD', str(name_str))
    ascii_only = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')

    # 1b. Pre-clean alias check: catches 'M.Berrettini' BEFORE the dot is stripped.
    #     The post-clean check below handles fully-stripped variants.
    pre_clean = re.sub(r'\s+', ' ', ascii_only.lower().strip())
    if pre_clean in TOP_50_ALIASES:
        return TOP_50_ALIASES[pre_clean]

    # 2. Lowercase + strip non-alphanumeric (keeps spaces)
    cleaned = re.sub(r'[^a-z\s]', '', ascii_only.lower()).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)  # collapse multiple spaces

    # 3. Post-clean alias check (catches already-clean variants like 'de minaur a')
    if cleaned in TOP_50_ALIASES:
        return TOP_50_ALIASES[cleaned]

    # 4. Parse into canonical form
    # Multi-word surname prefixes: 'de', 'del', 'van', 'von', 'di', 'le'
    # Audit Finding 2: without this, 'Alex de Minaur' -> 'minaur-a' while
    # the sheet has 'de minaur a' -> 'de minaur-a'. These WOULD NOT match.
    SURNAME_PREFIXES = {'de', 'del', 'van', 'von', 'di', 'le'}

    parts = cleaned.split()
    if not parts:
        return 'unknown'

    if len(parts) >= 2:
        # Scenario A: Tennis-Data sheet format ('de minaur a', 'van de zandschulp b')
        #   Last token is a single initial letter -> already 'surname initial' form
        if len(parts[-1]) == 1:
            return f"{' '.join(parts[:-1])}-{parts[-1]}"

        # Scenario B: ESPN/full-name feed with compound surname ('alex de minaur',
        #   'juan martin del potro', 'alex van de zandschulp').
        #   Scan ALL parts from index 1 onwards for the first surname prefix.
        #   Everything from that prefix to the end becomes the compound surname.
        prefix_idx = next(
            (i for i in range(1, len(parts)) if parts[i] in SURNAME_PREFIXES),
            None
        )
        if prefix_idx is not None:
            surname_compound = ' '.join(parts[prefix_idx:])
            initial = parts[0][0]
            return f"{surname_compound}-{initial}"

        # Scenario C: Standard 'firstname surname' ('jannik sinner' -> 'sinner-j')
        return f"{parts[-1]}-{parts[0][0]}"


    # Single word token
    return parts[0]


# For backwards compatibility
normalize_name = normalize_tennis_name


def _get_retirement_risk(player_key: str) -> float:
    """Return this player's historical retirement-involvement rate (0.0 to 1.0)."""
    total = _match_counts.get(player_key, 0)
    if total < 5:
        return 0.0
    return _retirement_counts.get(player_key, 0) / total


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
    """
    Compute a player's win rate on a specific surface.

    Uses normalize_tennis_name() on both the lookup name and the sheet values
    so accents, dots, and trailing-space variants all resolve to the same
    canonical 'surname-initial' key. A difflib fuzzy fallback catches any
    remaining near-misses without falling through to league average.
    """
    player_key = normalize_tennis_name(player_name)
    surname    = player_key.split('-')[0]  # e.g. 'alcaraz' from 'alcaraz-c'

    surf_df = df[df['Surface'].str.lower() == surface.lower()] if 'Surface' in df.columns else df
    if surf_df.empty:
        return None

    winner_col = 'Winner' if 'Winner' in surf_df.columns else 'winner_name'
    loser_col  = 'Loser'  if 'Loser'  in surf_df.columns else 'loser_name'

    # Normalize all sheet names to canonical keys (cached via apply)
    w_keys = surf_df[winner_col].astype(str).apply(normalize_tennis_name)
    l_keys = surf_df[loser_col].astype(str).apply(normalize_tennis_name)

    # Exact canonical key match
    wins   = surf_df[w_keys == player_key]
    losses = surf_df[l_keys == player_key]

    # Surname-prefix fallback (covers multi-word surnames like 'de minaur')
    if len(wins) + len(losses) < 3:
        wins   = surf_df[w_keys.str.startswith(surname)]
        losses = surf_df[l_keys.str.startswith(surname)]

    # Difflib fuzzy fallback: finds the closest key in the dataset
    if len(wins) + len(losses) < 3:
        all_keys = set(w_keys.tolist() + l_keys.tolist())
        candidates = difflib.get_close_matches(player_key, all_keys, n=1, cutoff=0.80)
        if candidates:
            best = candidates[0]
            wins   = surf_df[w_keys == best]
            losses = surf_df[l_keys == best]

    total = len(wins) + len(losses)
    if total < 5:
        return None
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

    Uses the normalized break-point ratio for P(set win):
      P(A wins set) = hA*(1-hB) / (hA*(1-hB) + (1-hA)*hB)
    where hA = P(A holds), hB = P(B holds).

    This correctly captures serve dominance: at 97.9% vs 86% hold,
    player A wins the set ~88% of the time.
    """
    hA = _p_server_wins_game(serve_p1)   # P1 hold rate
    hB = _p_server_wins_game(serve_p2)   # P2 hold rate

    # P1 breaks P2
    bA = 1.0 - hB
    # P2 breaks P1
    bB = 1.0 - hA

    numerator   = hA * bA          # P1 holds AND breaks
    denominator = hA * bA + bB * hB  # same + P2 holds AND breaks

    if denominator < 1e-9:
        p_set = 0.5
    else:
        p_set = max(0.01, min(0.99, numerator / denominator))

    # Match probability
    if sets_target == 2:  # Best of 3
        q = 1.0 - p_set
        return p_set ** 2 + 2.0 * p_set ** 2 * q
    else:  # Best of 5
        q = 1.0 - p_set
        return p_set ** 3 + 3.0 * p_set ** 3 * q + 6.0 * p_set ** 3 * q ** 2


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
    from surface_engine import SURFACE_MODIFIERS

    # League average opponent serve prob
    league_serve = LEAGUE_SERVE_PROFILES[tour]['_implied_serve_prob']
    sets_target = 2  # use Best-of-3 for calibration (most matches)

    lo, hi = 0.35, 0.84
    for _ in range(50):
        mid = (lo + hi) / 2.0
        # Apply surface multiplicatively (audit Finding 1 — no additive shifts)
        surf_mod     = SURFACE_MODIFIERS.get((tour, surface), 1.00)
        p_adjusted   = max(0.01, min(0.99, mid          * surf_mod))
        opp_adjusted = max(0.01, min(0.99, league_serve * surf_mod))

        predicted = _expected_match_win_prob(p_adjusted, opp_adjusted, sets_target)

        if abs(predicted - player_win_rate) < tolerance:
            break
        if predicted < player_win_rate:
            lo = mid
        else:
            hi = mid

    return max(0.40, min(0.84, mid))


def _serve_prob_to_profile(serve_prob: float, tour: str) -> dict:
    """
    Convert a bare serve point probability into a full serve profile
    by scaling the league-average profile proportionally.

    This allows the Markov engine to run with full profile compatibility.
    """
    league = LEAGUE_SERVE_PROFILES[tour]
    league_sp = league['_implied_serve_prob']
    scale = serve_prob / league_sp if league_sp > 0 else 1.0

    # Scale serving attributes proportionally; clamp to realistic bounds
    fsw = min(0.88, league['first_serve_win_pct'] * scale)
    ssw = min(0.72, league['second_serve_win_pct'] * scale)

    # Audit Finding 1 fix: RPW is NOT the mathematical inverse of serve dominance.
    # Djokovic is an elite server AND an elite returner. Forcing rpw = league/scale
    # artificially crushes return capability for every dominant server, inflating
    # hold rates toward 100% and blowing up Total Games O/U projections.
    # Fix: anchor RPW to the tour baseline unless explicit sheet data overrides it.
    rpw = league['return_points_won_pct']

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

    # Fix 1: Attach retirement risk so consensus engine can void Total Games O/U
    player_key = normalize_tennis_name(player_name)
    ret_risk = _get_retirement_risk(player_key)
    profile['retirement_risk_pct'] = round(ret_risk, 4)
    profile['retirement_risk_flag'] = ret_risk >= 0.08  # flag if >=8% involvement

    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)

    return profile



# ============================================================
# ESPN Schedule Fetcher
# ============================================================

def fetch_espn_tennis_schedule(tour: str = 'ATP') -> list:
    """
    Fetch today's scheduled singles matches from ESPN's public API.

    Fix: ESPN structures competitions inside groupings[], NOT directly on the
    event object. Drilling into event.competitions[] always returns empty.
    This parser targets the correct grouping slug (mens-singles / womens-singles)
    and filters to STATUS_SCHEDULED matches only.

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

    # Target slug: only singles — doubles/mixed require a different model
    target_slug = 'mens-singles' if tour == 'ATP' else 'womens-singles'

    matches = []
    for event in data.get('events', []):
        tournament_name = event.get('name', 'Unknown')

        for grouping_block in event.get('groupings', []):
            g_slug = grouping_block.get('grouping', {}).get('slug', '')
            if g_slug != target_slug:
                continue

            for comp in grouping_block.get('competitions', []):
                status = comp.get('status', {}).get('type', {}).get('name', '')

                # Only surface matches still to be played
                if status != 'STATUS_SCHEDULED':
                    continue

                competitors = comp.get('competitors', [])
                if len(competitors) < 2:
                    continue

                # Sort by ESPN's 'order' field — lower = listed first
                competitors = sorted(competitors, key=lambda x: x.get('order', 99))
                p1 = competitors[0].get('athlete', {})
                p2 = competitors[1].get('athlete', {})

                matches.append({
                    'match_id':        comp.get('id', ''),
                    'p1_name':         p1.get('displayName', 'Unknown'),
                    'p2_name':         p2.get('displayName', 'Unknown'),
                    'tournament_name': tournament_name,
                    'status':          status,
                    'tour':            tour,
                    'round':           comp.get('round', {}).get('number', 0),
                    'date':            comp.get('date', ''),
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
