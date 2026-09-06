"""
build_corner_booking_profiles.py
──────────────────────────────────
Builds per-team historical corner & booking point profiles by fetching
the last N completed fixtures per team from /fixtures/statistics.

Usage:
    python build_corner_booking_profiles.py                        # all discovered leagues (weekly)
    python build_corner_booking_profiles.py --today-only           # only today's active leagues (daily)
    python build_corner_booking_profiles.py --league 39            # specific league
    python build_corner_booking_profiles.py --last 5               # use last 5 fixtures per team
    python build_corner_booking_profiles.py --today-only --date 2026-08-24  # specific date

Output: data/football/team_profiles_{league_id}.json
"""

import os
import sys
import json
import time
import argparse
import glob
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

load_dotenv()

API_KEY  = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "football")
CHECKPOINT_PATH = os.path.join(DATA_DIR, "_profiles_checkpoint.json")

YELLOW_CARD_PTS = 10
RED_CARD_PTS    = 25

# ── Bayesian shrinkage & prior-season settings ─────────────────────────────
MIN_RELIABLE     = 8    # games before own data outweighs the prior
SHRINKAGE_K      = 8    # weight of league prior (stricter: needs 8+ games to trust own data ≥50%)
PRIOR_SEASON     = 2025 # fallback season to query API when current season is sparse


LEAGUE_PRIORITY = {
    2: 1, 3: 2, 848: 3, 13: 4, 11: 5,
    39: 10,
    140: 20, 135: 21, 78: 22,
    61: 30, 88: 31, 94: 32,
    45: 40, 48: 41, 143: 42, 137: 43, 81: 44, 66: 45,
    144: 50, 203: 51, 179: 52, 218: 53, 207: 54, 197: 55, 345: 56,
    40: 60, 141: 61, 136: 62, 79: 63, 62: 64,
    71: 70, 73: 71, 128: 72, 239: 73, 242: 74, 265: 75, 268: 76,
    262: 80, 253: 81,
    307: 90,
    119: 100, 113: 101, 103: 102, 210: 103, 285: 104, 106: 105, 283: 106, 89: 107,
    98: 110, 292: 111, 188: 112,
    254: 120
}

# Shared mutable call counter (module-level so safe_get can update it)
_api_calls = {"count": 0, "budget": 4000}


class BudgetExhausted(Exception):
    """Raised when the API call budget is reached."""
    pass


def safe_get(endpoint, params, retries=2):
    url = f"{BASE_URL}{endpoint}"
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code == 429:
                print("  ⏳ Rate limited, waiting 10s...")
                time.sleep(10)
                continue
            r.raise_for_status()
            _api_calls["count"] += 1
            # Hard budget cap — stop before exhausting the day's allowance
            if _api_calls["count"] >= _api_calls["budget"]:
                raise BudgetExhausted(
                    f"API budget reached ({_api_calls['budget']} calls). "
                    f"Remaining calls reserved for predictions."
                )
            return r.json()
        except BudgetExhausted:
            raise   # propagate immediately
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"  ⚠️  {endpoint} failed: {e}")
    return {}


def fetch_prior_season_raw(team_id: int, league_id: int, last: int) -> dict:
    """
    Fetch last N FT fixtures from PRIOR_SEASON for a team via the API.
    Returns raw aggregated stats dict (corners_for_list, etc.) or empty dict on failure.
    Costs API credits, so only called when current season n < MIN_RELIABLE.
    """
    data = safe_get("/fixtures", {
        "team": team_id, "league": league_id, "season": PRIOR_SEASON,
        "status": "FT", "last": last
    })
    fixtures = data.get("response", [])
    if not fixtures:
        return {}

    corners_for_list = []
    corners_ag_list  = []
    yellow_list      = []
    red_list         = []
    fouls_list       = []
    booking_pts_list = []
    shots_total_list = []

    for fix in fixtures:
        fid = str(fix["fixture"]["id"])
        is_home = fix["teams"]["home"]["id"] == team_id

        stat_data = safe_get("/fixtures/statistics", {"fixture": int(fid)})
        time.sleep(0.15)

        stats_by_team = {}
        for block in stat_data.get("response", []):
            tid  = block["team"]["id"]
            vals = {s["type"]: s["value"] for s in block.get("statistics", [])}
            stats_by_team[tid] = vals

        team_stats = stats_by_team.get(team_id, {})
        opp_ids    = [tid for tid in stats_by_team if tid != team_id]
        opp_stats  = stats_by_team.get(opp_ids[0], {}) if opp_ids else {}

        def _int(d, key, default=0):
            v = d.get(key)
            if v is None:
                return default
            try:
                return int(str(v).replace("%", ""))
            except (ValueError, TypeError):
                return default

        corners_for = _int(team_stats, "Corner Kicks")
        corners_ag  = _int(opp_stats,  "Corner Kicks")
        yellow      = _int(team_stats, "Yellow Cards")
        red         = _int(team_stats, "Red Cards")
        fouls       = _int(team_stats, "Fouls")
        shots       = _int(team_stats, "Total Shots")
        booking_pts = (yellow * YELLOW_CARD_PTS) + (red * RED_CARD_PTS)

        if corners_for + corners_ag + yellow + shots > 0:
            corners_for_list.append(corners_for)
            corners_ag_list.append(corners_ag)
            yellow_list.append(yellow)
            red_list.append(red)
            fouls_list.append(fouls)
            booking_pts_list.append(booking_pts)
            shots_total_list.append(shots)

    if not corners_for_list:
        return {}

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    return {
        "n":              len(corners_for_list),
        "avg_corners_for":     avg(corners_for_list),
        "avg_corners_against": avg(corners_ag_list),
        "avg_yellow_cards":    avg(yellow_list),
        "avg_red_cards":       avg(red_list),
        "avg_fouls":           avg(fouls_list),
        "avg_booking_pts":     avg(booking_pts_list),
        "avg_shots_total":     avg(shots_total_list),
    }


def apply_bayesian_shrinkage(raw_profile: dict, league_prior: dict) -> dict:
    """
    Shrink each team metric toward the league prior.
    Formula: shrunk = (n * observed + k * prior) / (n + k)
    k = SHRINKAGE_K (8 = stricter; team needs 8+ games to be >=50% weighted)
    """
    if not league_prior or raw_profile.get("quarantined"):
        return raw_profile

    n = raw_profile.get("sample_size", 0)
    k = SHRINKAGE_K

    metrics = [
        "avg_corners_for", "avg_corners_against", "avg_total_corners",
        "home_corners_for", "home_corners_against", 
        "away_corners_for", "away_corners_against",
        "avg_yellow_cards", "avg_red_cards", "avg_fouls",
        "avg_booking_pts", "avg_shots_total"
    ]

    shrunk = dict(raw_profile)
    for m in metrics:
        obs   = raw_profile.get(m, 0.0)
        prior = league_prior.get(m, obs)   # fallback to own value if prior missing
        shrunk[m] = round((n * obs + k * prior) / (n + k), 2)

    shrunk["shrinkage_applied"] = True
    shrunk["league_prior_weight"] = round(k / (n + k), 3)
    return shrunk


def blend_with_prior_season(current: dict, prior: dict, current_n: int) -> dict:
    """
    Linearly blend current-season shrunk stats with prior-season stats.
    alpha = min(1.0, n / MIN_RELIABLE)
    alpha=0 → all prior season, alpha=1 → all current season
    """
    if not prior or current.get("quarantined"):
        return current

    alpha = min(1.0, current_n / MIN_RELIABLE)
    blended = dict(current)

    metrics = [
        "avg_corners_for", "avg_corners_against", "avg_total_corners",
        "home_corners_for", "home_corners_against", 
        "away_corners_for", "away_corners_against",
        "avg_yellow_cards", "avg_red_cards", "avg_fouls",
        "avg_booking_pts", "avg_shots_total"
    ]
    for m in metrics:
        cur_val  = current.get(m, 0.0)
        prev_val = prior.get(m, cur_val)
        blended[m] = round(alpha * cur_val + (1 - alpha) * prev_val, 2)

    blended["prior_season_blend_alpha"] = round(alpha, 3)
    blended["prior_season_used"]        = (PRIOR_SEASON if alpha < 1.0 else None)
    return blended


def compute_league_prior(profiles: dict) -> dict:
    """
    Compute the unweighted mean of each metric across all non-quarantined teams
    in a league. Used as the Bayesian prior for shrinkage.
    """
    valid = [p for p in profiles.values() if not p.get("quarantined") and p.get("sample_size", 0) > 0]
    if not valid:
        return {}

    metrics = [
        "avg_corners_for", "avg_corners_against", "avg_total_corners",
        "home_corners_for", "home_corners_against", 
        "away_corners_for", "away_corners_against",
        "avg_yellow_cards", "avg_red_cards", "avg_fouls",
        "avg_booking_pts", "avg_shots_total"
    ]

    prior = {}
    for m in metrics:
        vals = [p[m] for p in valid if m in p]
        prior[m] = round(sum(vals) / len(vals), 2) if vals else 0.0
    return prior


def assign_confidence(n: int) -> str:
    if n >= MIN_RELIABLE:
        return "high"
    elif n >= 4:
        return "medium"
    else:
        return "low"


def build_profile_for_team(team_id: int, league_id: int, season: int, last: int, old_prof: dict) -> dict | None:
    """
    Fetch the last `last` matches for `team_id`, extract corners/cards,
    and return an aggregated dict with caching.
    """
    data = safe_get("/fixtures", {
        "team": team_id, "league": league_id, "season": season,
        "status": "FT", "last": last
    })
    fixtures = data.get("response", [])
    if not fixtures:
        return None

    corners_for_list    = []
    corners_ag_list     = []
    home_corners_for    = []
    home_corners_ag     = []
    away_corners_for    = []
    away_corners_ag     = []
    yellow_list         = []
    red_list            = []
    fouls_list          = []
    booking_pts_list    = []
    shots_total_list    = []
    
    cached_history = old_prof.get("fixture_history", {}) if old_prof else {}
    new_history = {}

    for fix in fixtures:
        fid = str(fix["fixture"]["id"])
        
        is_home = fix["teams"]["home"]["id"] == team_id
        
        # If it's already cached, grab stats locally (0 API calls)
        if fid in cached_history:
            cached = cached_history[fid]
            corners_for_list.append(cached["corners_for"])
            corners_ag_list.append(cached["corners_ag"])
            
            if is_home:
                home_corners_for.append(cached["corners_for"])
                home_corners_ag.append(cached["corners_ag"])
            else:
                away_corners_for.append(cached["corners_for"])
                away_corners_ag.append(cached["corners_ag"])
                
            yellow_list.append(cached["yellow"])
            red_list.append(cached["red"])
            fouls_list.append(cached.get("fouls", 0))
            booking_pts_list.append(cached["booking_pts"])
            shots_total_list.append(cached.get("shots", 0))
            new_history[fid] = cached
            continue
        side    = "home" if is_home else "away"
        opp_side = "away" if is_home else "home"

        stat_data = safe_get("/fixtures/statistics", {"fixture": int(fid)})
        time.sleep(0.15)   # be gentle with rate limits

        stats_by_team = {}
        for block in stat_data.get("response", []):
            tid  = block["team"]["id"]
            vals = {s["type"]: s["value"] for s in block.get("statistics", [])}
            stats_by_team[tid] = vals

        team_stats = stats_by_team.get(team_id, {})
        opp_ids    = [tid for tid in stats_by_team if tid != team_id]
        opp_stats  = stats_by_team.get(opp_ids[0], {}) if opp_ids else {}

        def _int(d, key, default=0):
            v = d.get(key)
            if v is None:
                return default
            try:
                return int(str(v).replace("%", ""))
            except (ValueError, TypeError):
                return default

        corners_for  = _int(team_stats, "Corner Kicks")
        corners_ag   = _int(opp_stats,  "Corner Kicks")
        yellow       = _int(team_stats, "Yellow Cards")
        red          = _int(team_stats, "Red Cards")
        fouls        = _int(team_stats, "Fouls")
        shots        = _int(team_stats, "Total Shots")
        booking_pts  = (yellow * YELLOW_CARD_PTS) + (red * RED_CARD_PTS)

        if corners_for + corners_ag + yellow + shots > 0:   # skip blank stat returns
            corners_for_list.append(corners_for)
            corners_ag_list.append(corners_ag)
            
            if is_home:
                home_corners_for.append(corners_for)
                home_corners_ag.append(corners_ag)
            else:
                away_corners_for.append(corners_for)
                away_corners_ag.append(corners_ag)
                
            yellow_list.append(yellow)
            red_list.append(red)
            fouls_list.append(fouls)
            booking_pts_list.append(booking_pts)
            shots_total_list.append(shots)
            
            new_history[fid] = {
                "corners_for": corners_for,
                "corners_ag": corners_ag,
                "yellow": yellow,
                "red": red,
                "fouls": fouls,
                "shots": shots,
                "booking_pts": booking_pts
            }

    n = len(corners_for_list)
    if n == 0:
        return {"quarantined": True, "reason": "No corner/booking stats in FT fixtures"}

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    def blended_venue_avg(venue_lst, overall_lst):
        """Blend venue-specific average with overall if sample < 5"""
        v_avg = avg(venue_lst)
        o_avg = avg(overall_lst)
        n_venue = len(venue_lst)
        if n_venue >= 5: return v_avg
        # Linear blend: n/5 weight to venue, (5-n)/5 to overall
        w = n_venue / 5.0
        return round(w * v_avg + (1 - w) * o_avg, 2)

    # Calculate Form Slope (Last 5 matches corners_for)
    # y = corners, x = [1, 2, 3, 4, 5] (where 5 is most recent)
    # Slope = sum((x - mean_x) * (y - mean_y)) / sum((x - mean_x)^2)
    # The list is from oldest to newest if they are ordered that way. 
    # API usually returns newest to oldest or oldest to newest. We need to be careful.
    # Let's assume the order in corners_for_list is newest last or oldest last.
    # Actually, fixtures from API with `last=N` returns newest first. 
    # Let's reverse to get oldest first for slope calculation:
    recent_5 = list(reversed(corners_for_list))[-5:] if len(corners_for_list) >= 5 else []
    corner_form_slope = 0.0
    if len(recent_5) == 5:
        x = [1, 2, 3, 4, 5]
        mean_x = 3
        mean_y = sum(recent_5) / 5
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, recent_5))
        denominator = 10.0 # sum((x-3)^2) = 4 + 1 + 0 + 1 + 4 = 10
        corner_form_slope = round(numerator / denominator, 2)

    return {
        "team_id":              team_id,
        "avg_corners_for":      avg(corners_for_list),
        "avg_corners_against":  avg(corners_ag_list),
        "avg_total_corners":    avg([f + a for f, a in zip(corners_for_list, corners_ag_list)]),
        
        # Venue-specific stats
        "home_corners_for":     blended_venue_avg(home_corners_for, corners_for_list),
        "home_corners_against": blended_venue_avg(home_corners_ag, corners_ag_list),
        "away_corners_for":     blended_venue_avg(away_corners_for, corners_for_list),
        "away_corners_against": blended_venue_avg(away_corners_ag, corners_ag_list),
        
        "corner_form_slope":    corner_form_slope,
        
        "avg_yellow_cards":     avg(yellow_list),
        "avg_red_cards":        avg(red_list),
        "avg_fouls":            avg(fouls_list),
        "avg_booking_pts":      avg(booking_pts_list),
        "avg_shots_total":      avg(shots_total_list),
        "sample_size":          n,
        "confidence":           assign_confidence(n),
        "built_at":             datetime.utcnow().isoformat(),
        "fixture_history":      new_history
    }


def corners_prediction(home_profile: dict, away_profile: dict) -> dict:
    """
    Predict corner totals and booking points for a match
    given the two team profiles.

    Emits YES/NO/PASS signals (corner_call, booking_call) with minimum
    confidence thresholds:
      - Corner call: Poisson probability >= 65% AND expected margin >= 1.5
      - Booking call: >= 65% probability above/below 30/40 pts threshold
    """
    if not home_profile or not away_profile:
        return {}

    if home_profile.get("quarantined") or away_profile.get("quarantined"):
        return {}
        
    # Default to non-venue splits if venue splits are missing (e.g. from old data)
    h_for = home_profile.get("home_corners_for", home_profile["avg_corners_for"])
    a_ag  = away_profile.get("away_corners_against", away_profile["avg_corners_against"])
    a_for = away_profile.get("away_corners_for", away_profile["avg_corners_for"])
    h_ag  = home_profile.get("home_corners_against", home_profile["avg_corners_against"])

    # ── Corner expected values ────────────────────────────────────────────
    exp_home_corners = (h_for + a_ag) / 2
    exp_away_corners = (a_for + h_ag) / 2
    
    # Form slope modifier (caps at +/- 1.0 corners)
    h_slope = max(-1.0, min(1.0, home_profile.get("corner_form_slope", 0.0) * 0.5))
    a_slope = max(-1.0, min(1.0, away_profile.get("corner_form_slope", 0.0) * 0.5))
    
    exp_home_corners += h_slope
    exp_away_corners += a_slope
    
    # Ensure they don't go negative
    exp_home_corners = round(max(0.5, exp_home_corners), 1)
    exp_away_corners = round(max(0.5, exp_away_corners), 1)
    
    exp_total = round(exp_home_corners + exp_away_corners, 1)

    import math

    def poisson_cdf(lam, k):
        """P(X <= k) for Poisson(lam)."""
        if lam <= 0:
            return 1.0
        total = 0.0
        for i in range(k + 1):
            total += (math.e ** -lam) * (lam ** i) / math.factorial(i)
        return min(total, 1.0)

    over_8_5  = round((1 - poisson_cdf(exp_total, 8))  * 100)
    over_9_5  = round((1 - poisson_cdf(exp_total, 9))  * 100)
    over_10_5 = round((1 - poisson_cdf(exp_total, 10)) * 100)
    over_11_5 = round((1 - poisson_cdf(exp_total, 11)) * 100)

    # ── Standard Vegas line: 10.5 ─────────────────────────────────────────
    # 10.5 is the canonical bookmaker corners total line (avg actual = 10.0).
    # Previously we picked the max-edge line across [8.5, 9.5, 10.5, 11.5]
    # which gravitated to OVER 8.5 / UNDER 11.5 — lines not offered at
    # real odds. Fixing to 10.5 aligns predictions with actual betting markets.
    CORNER_LINES   = [10.5]
    CORNER_PROBS   = [over_10_5]
    CORNER_THRES   = 65   # minimum % to call YES or NO
    CORNER_MARGIN  = 1.5  # expected total must be >= 1.5 clear of the line

    corner_call      = "PASS"
    corner_call_line = None
    corner_call_pct  = None
    best_edge        = 0

    for line, p_over in zip(CORNER_LINES, CORNER_PROBS):
        p_under = 100 - p_over
        edge_over  = p_over  - 50  # positive = over leaning
        edge_under = p_under - 50  # positive = under leaning

        if p_over >= CORNER_THRES and (exp_total - line) >= CORNER_MARGIN:
            if edge_over > best_edge:
                best_edge        = edge_over
                corner_call      = "YES"
                corner_call_line = f"OVER {line}"
                corner_call_pct  = p_over

        if p_under >= CORNER_THRES and (line - exp_total) >= CORNER_MARGIN:
            if edge_under > best_edge:
                best_edge        = edge_under
                corner_call      = "NO"
                corner_call_line = f"UNDER {line}"
                corner_call_pct  = p_under

    # Legacy recommendation field (kept for backward compat)
    if over_10_5 >= 55:
        corner_rec = "OVER 10.5"
    elif over_9_5 >= 60:
        corner_rec = "OVER 9.5"
    elif over_9_5 < 35:
        corner_rec = "UNDER 9.5"
    else:
        corner_rec = "PASS"

    # ── Booking expected values ───────────────────────────────────────────
    exp_total_booking = round(home_profile["avg_booking_pts"] + away_profile["avg_booking_pts"], 1)
    exp_total_yellows = round(home_profile["avg_yellow_cards"] + away_profile["avg_yellow_cards"], 1)

    over_30_bk = round((1 - poisson_cdf(exp_total_booking / 10, 2)) * 100)
    over_40_bk = round((1 - poisson_cdf(exp_total_booking / 10, 3)) * 100)

    # ── Booking YES/NO/PASS call (League Normalized) ──────────────────────
    # Determine the league's baseline points (fallback to 40 if missing)
    # The league prior is typically passed inside the profile or we can extract it.
    # We will use the home team's avg_booking_pts as a proxy if league prior is missing,
    # but to do this properly we should pass league_avg_booking_pts. 
    # For now, we extract it from a new key we will add to profiles: 'league_avg_booking_pts'
    league_avg_team_pts = home_profile.get("league_avg_booking_pts", 20.0)
    league_avg_match_pts = league_avg_team_pts * 2
    
    # We test lines around the league average (rounded to nearest 10)
    base_line = round(league_avg_match_pts / 10) * 10
    if base_line < 20: base_line = 20
    if base_line > 70: base_line = 70
    
    # Test base_line and base_line + 10
    lines_to_test = [base_line, base_line + 10]
    if base_line > 20: lines_to_test.insert(0, base_line - 10)
    
    BOOKING_THRES   = 65
    BOOKING_MARGIN  = 5.0

    booking_call      = "PASS"
    booking_call_line = None
    booking_call_pct  = None
    best_bk_edge      = 0

    for line in lines_to_test:
        # Calculate poisson prob for > line
        # line / 10 because poisson is calculated using units of 10 points (1 card)
        p_over = round((1 - poisson_cdf(exp_total_booking / 10, int(line / 10) - 1)) * 100)
        p_under = 100 - p_over
        
        edge_over = p_over - 50
        edge_under = p_under - 50
        
        if p_over >= BOOKING_THRES and (exp_total_booking - line) >= BOOKING_MARGIN:
            if edge_over > best_bk_edge:
                best_bk_edge      = edge_over
                booking_call      = "YES"
                booking_call_line = f"OVER {line} PTS"
                booking_call_pct  = p_over
                
        if p_under >= BOOKING_THRES and (line - exp_total_booking) >= BOOKING_MARGIN:
            if edge_under > best_bk_edge:
                best_bk_edge      = edge_under
                booking_call      = "NO"
                booking_call_line = f"UNDER {line} PTS"
                booking_call_pct  = p_under

    # Legacy booking recommendation (kept for backward compat)
    if exp_total_booking >= 40:
        booking_rec = "HIGH (Over 30 pts likely)"
    elif exp_total_booking >= 28:
        booking_rec = "MEDIUM"
    else:
        booking_rec = "LOW"

    return {
        "exp_home_corners":    exp_home_corners,
        "exp_away_corners":    exp_away_corners,
        "exp_total_corners":   exp_total,
        "over_8_5_pct":        over_8_5,
        "over_9_5_pct":        over_9_5,
        "over_10_5_pct":       over_10_5,
        "over_11_5_pct":       over_11_5,
        # ── YES/NO/PASS corner call ──
        "corner_call":         corner_call,       # "YES" | "NO" | "PASS"
        "corner_call_line":    corner_call_line,  # e.g. "OVER 9.5"
        "corner_call_pct":     corner_call_pct,   # e.g. 68
        "corner_recommendation": corner_rec,       # legacy
        # ── YES/NO/PASS booking call ──
        "booking_call":        booking_call,       # "YES" | "NO" | "PASS"
        "booking_call_line":   booking_call_line,  # e.g. "OVER 30 PTS"
        "booking_call_pct":    booking_call_pct,   # e.g. 71
        "exp_total_booking_pts":  exp_total_booking,
        "exp_total_yellows":      exp_total_yellows,
        "over_30_booking_pct":    over_30_bk,
        "over_40_booking_pct":    over_40_bk,
        "booking_recommendation": booking_rec,     # legacy
    }


def build_profiles_for_league(league_id: int, season: int, last: int) -> dict:
    """Fetch all playing teams in a league and build their profiles."""
    # Get team list from recent stats files or fixtures
    teams_data = safe_get("/teams", {"league": league_id, "season": season})
    teams = teams_data.get("response", [])
    if not teams:
        print(f"  No teams found for league {league_id}")
        return {}

    # Load existing to check for previous permanent quarantines
    existing_path = os.path.join(DATA_DIR, f"team_profiles_{league_id}.json")
    existing_teams = {}
    if os.path.exists(existing_path):
        try:
            with open(existing_path, encoding="utf-8") as f:
                ed = json.load(f)
                existing_teams = ed.get("teams", {})
        except Exception:
            pass

    # Preflight: one call to check if ANY completed fixtures exist for this league.
    # Saves N credits (one per team) for empty/early-season leagues.
    preflight = safe_get("/fixtures", {"league": league_id, "season": season, "status": "FT", "last": 1})
    if not preflight.get("response"):
        print(f"  League {league_id}: no FT fixtures yet — skipping all {len(teams)} teams (saves {len(teams)} credits)")
        return {}

    profiles = {}
    print(f"  Building profiles for {len(teams)} teams in league {league_id}...")

    teams_with_stats = 0
    teams_without_stats = 0

    for t in teams:
        team = t.get("team", {})
        tid  = team.get("id")
        name = team.get("name", "Unknown")
        if not tid:
            continue

        print(f"    {name} (id={tid})...", end=" ", flush=True)

        old_prof = existing_teams.get(str(tid), {})
        if old_prof.get("quarantined"):
            print("permanently quarantined")
            profiles[str(tid)] = old_prof
            teams_without_stats += 1
            if teams_without_stats >= 2 and teams_with_stats == 0:
                print(f"\n  [SMART QUARANTINE] League {league_id} provides no stats (cached). Quarantining entire league.")
                break
            continue

        profile = build_profile_for_team(tid, league_id, season, last, old_prof)
        if profile:
            if profile.get("quarantined"):
                print("quarantined (no stats)")
                profiles[str(tid)] = profile
                teams_without_stats += 1
                
                # SMART QUARANTINE LOGIC:
                # If the first 2 teams with FT fixtures return no stats across all their matches,
                # it's practically certain the league doesn't provide stats. Abort early.
                if teams_without_stats >= 2 and teams_with_stats == 0:
                    print(f"\n  [SMART QUARANTINE] League {league_id} provides no stats. Quarantining entire league.")
                    break
            else:
                profile["name"] = name
                profiles[str(tid)] = profile
                teams_with_stats += 1
                print(f"✓ ({profile['sample_size']} fixtures)")
        else:
            print("no data (no FT fixtures)")
        time.sleep(0.3)

    # ── Bayesian post-processing ──────────────────────────────────────────
    # Step A: compute league-level prior from all non-quarantined raw profiles
    league_prior = compute_league_prior(profiles)

    # Step B: for each non-quarantined profile, apply shrinkage + prior-season blend
    league_avg_booking_pts = league_prior.get("avg_booking_pts", 20.0)
    
    for tid_str, profile in list(profiles.items()):
        if profile.get("quarantined"):
            continue
            
        # Inject league average booking points so corners_prediction can normalize calls
        profile["league_avg_booking_pts"] = league_avg_booking_pts

        current_n = profile.get("sample_size", 0)

        # Apply Bayesian shrinkage toward league mean
        profile = apply_bayesian_shrinkage(profile, league_prior)

        # If under-sampled, fetch prior season and blend in
        if current_n < MIN_RELIABLE:
            try:
                tid_int = int(tid_str)
                print(f"    Team {tid_str}: n={current_n} < {MIN_RELIABLE}, fetching prior season {PRIOR_SEASON}...", end=" ", flush=True)
                prior_raw = fetch_prior_season_raw(tid_int, league_id, last)
                if prior_raw:
                    profile = blend_with_prior_season(profile, prior_raw, current_n)
                    print(f"blended (alpha={profile.get('prior_season_blend_alpha', '?')})")
                else:
                    print("no prior season data found")
            except Exception as e:
                print(f"prior season fetch failed: {e}")

        profiles[tid_str] = profile

    return profiles


def get_todays_league_ids(date_str: str) -> list[int]:
    """
    Fetch all leagues with fixtures on a given date.
    Used by --today-only to avoid rebuilding all leagues every day.
    """
    data = safe_get("/fixtures", {"date": date_str})
    league_ids = sorted(set(
        fix["league"]["id"]
        for fix in data.get("response", [])
        if fix.get("league", {}).get("id")
    ))
    print(f"Found {len(league_ids)} leagues with fixtures on {date_str}.")
    return league_ids


# ─────────────────────────────────────────────────────────────
# CHECKPOINT — resume interrupted builds
# ─────────────────────────────────────────────────────────────

def load_checkpoint() -> dict:
    """
    Returns the saved checkpoint, or empty dict if none.
    Schema: {"completed_leagues": [int, ...], "started_at": str, "calls_used": int}
    """
    if not os.path.exists(CHECKPOINT_PATH):
        return {}
    try:
        with open(CHECKPOINT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_checkpoint(completed: list[int], calls_used: int) -> None:
    """Persist progress so the next run can skip already-built leagues."""
    data = {
        "completed_leagues": completed,
        "calls_used": calls_used,
        "saved_at": datetime.utcnow().isoformat(),
    }
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  💾 Checkpoint saved — {len(completed)} league(s) done, {calls_used} API calls used.")


def clear_checkpoint() -> None:
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)
        print("  🗑️  Checkpoint cleared.")


def profile_age_hours(league_id: int) -> tuple[float | None, bool]:
    """
    Returns (age_hours, is_quarantined)
    """
    path = os.path.join(DATA_DIR, f"team_profiles_{league_id}.json")
    if not os.path.exists(path):
        return None, False
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        is_quar = data.get("league_quarantined", False)
        built_at = data.get("built_at", "")
        if not built_at:
            return None, is_quar
        # Parse ISO timestamp (UTC)
        dt = datetime.fromisoformat(built_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return round(age, 1), is_quar
    except Exception:
        return None, False


def print_status():
    """Print a table of all existing profile files and their freshness."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "team_profiles_*.json")))
    if not files:
        print("No profile files found in", DATA_DIR)
        return

    print(f"\n{'League':>8}  {'Teams':>6}  {'Built At (UTC)':>22}  {'Age':>8}  Status")
    print("-" * 65)
    now = datetime.now(timezone.utc)
    for fpath in files:
        lid = os.path.basename(fpath).replace("team_profiles_", "").replace(".json", "")
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            n_teams  = len(data.get("teams", {}))
            built_at = data.get("built_at", "?")
            age_h, is_quar = profile_age_hours(int(lid))
            age_str  = f"{age_h:.1f}h ago" if age_h is not None else "unknown"
            if is_quar:
                fresh = "🚫 quarantined"
            else:
                fresh = "✅ fresh" if (age_h is not None and age_h < 25) else "⚠️  stale"
            print(f"{lid:>8}  {n_teams:>6}  {built_at[:19]:>22}  {age_str:>8}  {fresh}")
        except Exception as e:
            print(f"{lid:>8}  (error reading: {e})")
    print(f"\nTotal: {len(files)} league profile(s)")


def main():
    parser = argparse.ArgumentParser(description="Build corner & booking profiles for football teams.")
    parser.add_argument("--league",        type=int,  help="Specific league ID to build")
    parser.add_argument("--season",        type=int,  default=2026)
    parser.add_argument("--last",          type=int,  default=0,
                        help="Last N completed fixtures per team (0 = auto: 5 for today-only, 12 for full)")
    parser.add_argument("--today-only",    action="store_true",
                        help="Only build profiles for leagues with games today (fast, daily-safe)")
    parser.add_argument("--priority-only", action="store_true",
                        help="Only build profiles for the predefined top-tier (priority) leagues")
    parser.add_argument("--date",          default="",
                        help="Target date for --today-only (YYYY-MM-DD, default: today UTC)")
    parser.add_argument("--max-age-hours", type=float, default=0,
                        help="Skip rebuild if profile is fresher than N hours (0 = auto: 23h daily, 160h weekly)")
    parser.add_argument("--force",         action="store_true",
                        help="Force rebuild even if profiles are fresh")
    parser.add_argument("--status",        action="store_true",
                        help="Print a table of existing profiles and their freshness, then exit")
    parser.add_argument("--max-calls",     type=int,  default=4000,
                        help="Max API calls before stopping gracefully (default: 4000, leaves ~3500 for predictions)")
    parser.add_argument("--resume",        action="store_true",
                        help="Resume from last checkpoint (skip already-completed leagues)")
    parser.add_argument("--clear-checkpoint", action="store_true",
                        help="Delete the saved checkpoint and exit")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    # --status: just show what's on disk and exit
    if args.status:
        print_status()
        # Also show checkpoint if present
        ckpt = load_checkpoint()
        if ckpt:
            print(f"\n📌 Checkpoint found — {len(ckpt.get('completed_leagues', []))} leagues completed, "
                  f"{ckpt.get('calls_used', 0)} calls used, saved at {ckpt.get('saved_at', '?')}")
            print("   Run with --resume to continue from this point.")
        return

    if args.clear_checkpoint:
        clear_checkpoint()
        return

    # Set the budget cap
    _api_calls["budget"] = args.max_calls
    print(f"API budget cap: {args.max_calls} calls")

    # Resolve how many fixtures to look back
    last = args.last if args.last > 0 else (5 if args.today_only else 12)

    # Resolve max-age for staleness check
    if args.force:
        max_age_hours = 0.0
    elif args.max_age_hours > 0:
        max_age_hours = args.max_age_hours
    elif args.today_only:
        max_age_hours = 96.0
    else:
        max_age_hours = 160.0

    if args.league:
        league_ids = [args.league]

    elif args.priority_only:
        league_ids = sorted(list(LEAGUE_PRIORITY.keys()), key=lambda x: LEAGUE_PRIORITY.get(x, 999))
        print(f"Building profiles for {len(league_ids)} priority leagues.")

    elif args.today_only:
        date_str = args.date or datetime.utcnow().strftime("%Y-%m-%d")
        league_ids = get_todays_league_ids(date_str)
        if not league_ids:
            print("No leagues found for today. Exiting.")
            return
        league_ids = sorted(league_ids, key=lambda x: LEAGUE_PRIORITY.get(x, 999))

    else:
        stat_files = glob.glob(os.path.join(DATA_DIR, "universal_*_stats.json"))
        league_ids = sorted(set(
            int(os.path.basename(f).split("_")[1])
            for f in stat_files
            if os.path.basename(f).split("_")[1].isdigit()
        ), key=lambda x: LEAGUE_PRIORITY.get(x, 999))
        print(f"Auto-discovered {len(league_ids)} leagues from existing stats files.")

    if not league_ids:
        print("No leagues to process.")
        return

    # Load checkpoint — skip already-completed leagues if --resume
    checkpoint = load_checkpoint() if args.resume else {}
    already_done = set(checkpoint.get("completed_leagues", []))
    if already_done:
        before = len(league_ids)
        league_ids = [lid for lid in league_ids if lid not in already_done]
        print(f"Resuming: skipping {before - len(league_ids)} already-completed league(s) from checkpoint.")

    print(f"Processing {len(league_ids)} league(s) | last={last} fixtures | "
          f"max_age={max_age_hours}h | budget={args.max_calls} calls")

    built = skipped = 0
    completed_this_run: list[int] = list(already_done)

    for lid in league_ids:
        # ── Staleness & Quarantine check ────────────────────────────────────
        age, is_quar = profile_age_hours(lid)
        
        if is_quar and not args.force:
            print(f"  League {lid:>6} — SKIP (permanently quarantined due to missing stats)")
            skipped += 1
            completed_this_run.append(lid)
            continue
            
        if not args.force and max_age_hours > 0 and age is not None and age < max_age_hours:
            print(f"  League {lid:>6} — SKIP (profile is {age:.1f}h old, threshold={max_age_hours}h)")
            skipped += 1
            completed_this_run.append(lid)  # treat fresh ones as done for checkpoint
            continue

        age_str = f"{age:.1f}h old" if age is not None else "no existing profile"
        print(f"\n{'='*60}")
        print(f"  League {lid}  [{age_str} → rebuilding]  "
              f"[API calls so far: {_api_calls['count']}/{args.max_calls}]")
        print(f"{'='*60}")

        try:
            profiles = build_profiles_for_league(lid, args.season, last)
        except BudgetExhausted as e:
            print(f"\n⚠️  {e}")
            print(f"   Stopping after {_api_calls['count']} calls. "
                  f"{len(completed_this_run)} league(s) completed this session.")
            save_checkpoint(completed_this_run, _api_calls["count"])
            print("   Run again with --resume to continue from here.")
            break

        if not profiles:
            continue

        # Check if ALL teams in this league returned quarantined
        all_quar = all(p.get("quarantined") for p in profiles.values()) if profiles else False

        out_path = os.path.join(DATA_DIR, f"team_profiles_{lid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "league_id": lid,
                "season":    args.season,
                "league_quarantined": all_quar,
                "built_at":  datetime.utcnow().isoformat(),
                "teams":     profiles
            }, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Saved {len(profiles)} team profiles → {out_path}  "
              f"[{_api_calls['count']} calls used]")
        built += 1
        completed_this_run.append(lid)

    else:
        # Loop completed without hitting budget — clear checkpoint
        if os.path.exists(CHECKPOINT_PATH):
            clear_checkpoint()

    print(f"\n✅ Done — {built} built, {skipped} skipped (fresh). "
          f"Total API calls this run: {_api_calls['count']}")


if __name__ == "__main__":
    main()
