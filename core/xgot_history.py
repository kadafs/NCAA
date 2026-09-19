"""
core/xgot_history.py
====================
xGOT Feedback Engine - computes rolling per-team shot-quality adjustment ratios
from graded prediction history.

Called once at the start of run_football_daily.py to produce a lightweight
dict of multipliers that are applied AFTER the base Poisson xg_h/xg_a is
computed, trimming systematic over/under-performance caused by:
  - Clinical finishing (xGOT << goals scored)
  - Poor shot conversion (xGOT >> goals scored)
  - Great / leaky goalkeeping

Output structure:
    {
        team_id (int): {
            "xgot_attack_adj":  float,  # multiplier on home/away xG (0.85-1.15)
            "xgot_defence_adj": float,  # multiplier on opponent xG  (0.85-1.15)
            "games":            int,    # number of graded games used
        },
        ...
    }

Adjustment is only applied when >= MIN_GAMES graded matches are available.
Cap is applied so adjustments never exceed +/-XGOT_CAP_PCT.
"""

import json
from pathlib import Path
from collections import defaultdict

# Config
DATA_DIR      = Path("data/football")
LOOKBACK_DAYS = 30      # max files to scan (one per day)
MIN_GAMES     = 5       # minimum graded games before any adjustment fires
XGOT_CAP_PCT  = 0.15   # maximum +/-15% adjustment

# Cup/knockout competition exclusion.
# Matches whose league name contains any of these keywords are skipped so
# B-squad cup appearances do not corrupt a team's domestic league rating.
# Note: lname is ASCII-normalised before matching so accented variants
# (e.g. "Ta\u00e7a" -> "taca", "Cop\u00f6" -> "copa") are caught correctly.
import unicodedata as _ud

_CUP_KEYWORDS = frozenset([
    'cup', 'copa', 'coupe', 'coppa', 'pokal', 'taca', 'kupa',
    'trophy', 'shield', 'supercup', 'supercoppa', 'super cup',
    'champions league', 'europa league', 'conference league',
    'nations league', 'world cup',
])


def _normalise(s: str) -> str:
    """Strip accents so e.g. Ta\u00e7a -> taca for keyword matching."""
    return _ud.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')


def _is_cup_match(league_name, country):
    lname = _normalise((league_name or '').lower())
    if (country or '').lower() in ('world', 'europe'):
        return True
    return any(kw in lname for kw in _CUP_KEYWORDS)


def build_xgot_adjustments(lookback: int = LOOKBACK_DAYS) -> dict:
    """
    Scan the last `lookback` prediction files and return per-team xGOT
    attack and defence adjustment multipliers.

    Returns:
        dict keyed by team_id (int) -> {xgot_attack_adj, xgot_defence_adj, games}
    """
    attack_records  = defaultdict(list)   # team_id -> list of xgot/xg ratios
    defence_records = defaultdict(list)   # team_id -> list of goals_conceded/xgot_faced ratios

    files = sorted(DATA_DIR.glob("universal_predictions_*.json"), reverse=True)[:lookback]

    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        for p in data.get("predictions", []):
            pmx = p.get("post_match_xgot")
            if not pmx:
                continue

            # Skip cup / continental / international fixtures
            if _is_cup_match(p.get("league"), p.get("country")):
                continue

            h_id = p.get("home_team_id")
            a_id = p.get("away_team_id")
            xg_h = p.get("xg_home") or 0.0
            xg_a = p.get("xg_away") or 0.0
            xgot_h = pmx.get("xgot_home") or 0.0
            xgot_a = pmx.get("xgot_away") or 0.0
            goals_h = p.get("actual_home_goals") or 0
            goals_a = p.get("actual_away_goals") or 0

            if xg_h <= 0.01 and xg_a <= 0.01:
                continue

            # Attack signal: ratio of actual xGOT to model xG prediction
            if h_id and xg_h > 0.05:
                attack_records[int(h_id)].append(xgot_h / xg_h)
            if a_id and xg_a > 0.05:
                attack_records[int(a_id)].append(xgot_a / xg_a)

            # Defence/GK signal: goals conceded / xGOT faced
            # Lower ratio = better GK; Higher ratio = leaky
            if h_id and xgot_a > 0.05:
                defence_records[int(h_id)].append(goals_a / xgot_a)
            if a_id and xgot_h > 0.05:
                defence_records[int(a_id)].append(goals_h / xgot_h)

    adjustments = {}
    all_team_ids = set(attack_records) | set(defence_records)
    baseline_gc_rate = 0.90  # typical goals_conceded / xgot_faced league average

    for tid in all_team_ids:
        a_recs = attack_records.get(tid, [])
        d_recs = defence_records.get(tid, [])
        n_games = max(len(a_recs), len(d_recs))

        if n_games < MIN_GAMES:
            continue

        if len(a_recs) >= MIN_GAMES:
            raw_attack = sum(a_recs) / len(a_recs)
            xgot_attack_adj = max(1.0 - XGOT_CAP_PCT, min(1.0 + XGOT_CAP_PCT, raw_attack))
        else:
            xgot_attack_adj = 1.0

        if len(d_recs) >= MIN_GAMES:
            raw_defence = sum(d_recs) / len(d_recs)
            defence_factor = raw_defence / baseline_gc_rate
            xgot_defence_adj = max(1.0 - XGOT_CAP_PCT, min(1.0 + XGOT_CAP_PCT, defence_factor))
        else:
            xgot_defence_adj = 1.0

        if xgot_attack_adj == 1.0 and xgot_defence_adj == 1.0:
            continue

        adjustments[tid] = {
            "xgot_attack_adj":  round(xgot_attack_adj, 4),
            "xgot_defence_adj": round(xgot_defence_adj, 4),
            "games":            n_games,
        }

    return adjustments


def apply_xgot_adjustment(
    xg_h: float,
    xg_a: float,
    home_team_id,
    away_team_id,
    adjustments: dict,
) -> tuple:
    """
    Apply xGOT-based multipliers to pre-computed Poisson xg_h / xg_a.

    home attack adj x away defence adj -> adjusted home xG
    away attack adj x home defence adj -> adjusted away xG

    Returns:
        (adjusted_xg_h, adjusted_xg_a)
    """
    if not adjustments:
        return xg_h, xg_a

    h_id = int(home_team_id) if home_team_id else None
    a_id = int(away_team_id) if away_team_id else None

    h_adj = adjustments.get(h_id, {})
    a_adj = adjustments.get(a_id, {})

    home_attack  = h_adj.get("xgot_attack_adj", 1.0)
    away_defence = a_adj.get("xgot_defence_adj", 1.0)
    adj_xg_h = round(xg_h * home_attack * away_defence, 3)

    away_attack  = a_adj.get("xgot_attack_adj", 1.0)
    home_defence = h_adj.get("xgot_defence_adj", 1.0)
    adj_xg_a = round(xg_a * away_attack * home_defence, 3)

    return max(0.25, adj_xg_h), max(0.25, adj_xg_a)
