"""
run_confidence_report.py
=========================
Runs the Model Confidence Score on any date's fixtures.

Data sources:
  - data/basketball/universal_predictions_{date}.json   (fixtures + volatility + spread)
  - data/basketball/basketball_leaderboard.json          (MAE + bias per team)

Usage:
    python run_confidence_report.py                    # today's fixtures
    python run_confidence_report.py --date 2026-05-06  # specific date
    python run_confidence_report.py --min_score 60     # only show score >= 60
    python run_confidence_report.py --tier top_domestic
    python run_confidence_report.py --league_id 72
"""

import json
import os
import sys
import csv
import argparse
import difflib
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from core.confidence_score import compute_confidence

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PREDICTIONS_DIR  = "data/basketball"
LEADERBOARD_PATH = "data/basketball/basketball_leaderboard.json"
CSV_OUTPUT_DIR   = "data/confidence_reports"

# Default values when a team has no leaderboard history
DEFAULT_MAE  = 12.0   # conservative — penalises unknown teams
DEFAULT_BIAS = 0.0    # no direction assumed


# ---------------------------------------------------------------------------
# Leaderboard loader — returns dict keyed by (team_name_lower, league_id)
# with fallback to (team_name_lower, None) for cross-league name lookups
# ---------------------------------------------------------------------------

def load_leaderboard() -> dict:
    """
    Load and index the leaderboard by normalised team name + league_id.
    Returns  { (name_lower, league_id): entry }
    """
    if not os.path.exists(LEADERBOARD_PATH):
        print(f"  [WARN] Leaderboard not found: {LEADERBOARD_PATH}")
        return {}

    data = json.load(open(LEADERBOARD_PATH, encoding="utf-8"))
    entries = data.get("leaderboard", [])

    index = {}
    for e in entries:
        name   = e.get("name", "").strip()
        lid    = e.get("league_id")
        key    = (name.lower(), lid)
        index[key] = e

    return index


def lookup_team(name: str, league_id: int, index: dict) -> dict | None:
    """
    Find leaderboard entry for a team.
    Priority:
      1. Exact name match within same league_id
      2. Fuzzy name match (>= 0.80 similarity) within same league_id

    NOTE: Cross-league fallback intentionally removed. Borrowing stats from
    a different competition produces misleading confidence scores.
    Teams with no league-specific history will use DEFAULT_MAE / DEFAULT_BIAS.
    """
    name_lower = name.lower().strip()

    # 1. Exact match in league
    if (name_lower, league_id) in index:
        return index[(name_lower, league_id)]

    # 2. Fuzzy match within same league only
    league_names = [(k[0], k[1]) for k in index if k[1] == league_id]
    if league_names:
        names_only = [k[0] for k in league_names]
        matches = difflib.get_close_matches(name_lower, names_only, n=1, cutoff=0.80)
        if matches:
            return index[(matches[0], league_id)]

    # No cross-league fallback — return None, caller will use defaults
    return None


def get_team_stats(name: str, league_id: int, index: dict) -> tuple:
    """
    Returns (mae, bias, graded_totals, flat_floor_rate, flat_floor_total, source) for a team.
    source is "leaderboard" when real data found, "defaults" when not.
    Falls back to defaults when team has no league-specific history.
    """
    entry = lookup_team(name, league_id, index)
    if entry:
        mae    = entry.get("mae",               DEFAULT_MAE)
        bias   = entry.get("avg_signed_delta",  DEFAULT_BIAS)
        graded = entry.get("graded_totals", 0)
        ff_rate  = entry.get("flat_floor_rate")   # 0.0-1.0 or None
        ff_total = entry.get("flat_floor_total", 0)
        return float(mae or DEFAULT_MAE), float(bias or DEFAULT_BIAS), int(graded), ff_rate, int(ff_total), "leaderboard"
    return DEFAULT_MAE, DEFAULT_BIAS, 0, None, 0, "defaults"



def check_clash_profile(home: str, away: str, league_id: int) -> bool:
    """
    Check if both teams have below-average offensive ratings
    and above-average (worse) defensive ratings.
    """
    if not league_id:
        return False
    cfg_path = os.path.join("configs", "leagues", f"{league_id}.json")
    if not os.path.exists(cfg_path):
        return False
    try:
        with open(cfg_path, "r", encoding="utf-8") as cf:
            cfg = json.load(cf)
        eff_pivot = cfg.get("eff_pivot", 108.0)
    except:
        return False

    stats_map = {}
    for suffix in ["adv", "srs"]:
        spath = os.path.join("data", f"bball_stats_{league_id}_{suffix}.json")
        if os.path.exists(spath):
            try:
                with open(spath, "r", encoding="utf-8") as sf:
                    sdata = json.load(sf)
                    for t in sdata.get("teams", []):
                        name = t["team_name"]
                        if name not in stats_map:
                            stats_map[name] = t
            except:
                pass

    def find_stats(team_name: str) -> dict | None:
        if not team_name:
            return None
        # 1. Exact match
        if team_name in stats_map:
            return stats_map[team_name]
        # 2. Case-insensitive match
        for name, stats in stats_map.items():
            if name.lower() == team_name.lower():
                return stats
        # 3. Substring match (e.g. "Leiden" inside "ZZ Leiden")
        for name, stats in stats_map.items():
            if team_name.lower() in name.lower() or name.lower() in team_name.lower():
                return stats
        # 4. Fuzzy match
        names = list(stats_map.keys())
        matches = difflib.get_close_matches(team_name, names, n=1, cutoff=0.60)
        if matches:
            return stats_map[matches[0]]
        return None

    sh = find_stats(home)
    sa = find_stats(away)
    if sh and sa:
        h_off, h_def = sh.get("adj_off"), sh.get("adj_def")
        a_off, a_def = sa.get("adj_off"), sa.get("adj_def")
        if h_off is not None and h_def is not None and a_off is not None and a_def is not None:
            return h_off < eff_pivot and a_off < eff_pivot and h_def > eff_pivot and a_def > eff_pivot
    return False

BAND_ORDER = ["[ELITE]   ", "[HIGH]    ", "[SOLID]   ", "[MODERATE]", "[LOW]     ", "[AVOID]   "]



def band_sort_key(band_label: str) -> int:
    """Lower index = higher confidence (for sorting)."""
    for i, b in enumerate(BAND_ORDER):
        if band_label.strip() in b.strip() or b.strip() in band_label.strip():
            return i
    return len(BAND_ORDER)


# ---------------------------------------------------------------------------
# Main report function
# ---------------------------------------------------------------------------

def run_report(date_str: str, min_score: float = 0.0, tier_filter: str = None,
               league_id_filter: int = None, show_components: bool = False,
               min_graded: int = 0, hidden_gems: bool = False, no_playoffs: bool = False):

    pred_path = os.path.join(PREDICTIONS_DIR, f"universal_predictions_{date_str}.json")
    if not os.path.exists(pred_path):
        print(f"\n  [ERROR] No predictions file for {date_str}: {pred_path}")
        return

    data       = json.load(open(pred_path, encoding="utf-8"))
    predictions = data.get("predictions", [])

    if not predictions:
        print(f"  No predictions found in {pred_path}")
        return

    print(f"\n  Loading leaderboard...")
    lb_index = load_leaderboard()
    print(f"  Loaded {len(lb_index)} team entries from leaderboard")

    rows = []

    for p in predictions:
        league_id  = p.get("league_id")
        league     = p.get("league", "Unknown")
        home       = p.get("home_team", "?")
        away       = p.get("away_team", "?")
        tier       = p.get("tier", "unknown")
        model_total = p.get("model_total", 0.0)
        xpts_h     = p.get("xpts_h", model_total / 2)
        xpts_a     = p.get("xpts_a", model_total / 2)

        # Filters
        if tier_filter and tier != tier_filter:
            continue
        if league_id_filter and league_id != league_id_filter:
            continue

        # Playoff filtering
        if no_playoffs:
            stage = p.get("stage", "").lower()
            playoff_keywords = ["final", "semi", "quarter", "playoff", "3rd place", "relegation"]
            if any(k in stage for k in playoff_keywords):
                continue

        # Spread from projected pts
        spread = abs((xpts_h or 0) - (xpts_a or 0))

        # Volatility — already in the prediction JSON
        vol_h = p.get("home_team_volatility") or DEFAULT_MAE
        vol_a = p.get("away_team_volatility") or DEFAULT_MAE

        # MAE + Bias — from leaderboard
        mae_h, bias_h, graded_h, ff_rate_h, ff_total_h, src_h = get_team_stats(home, league_id, lb_index)
        mae_a, bias_a, graded_a, ff_rate_a, ff_total_a, src_a = get_team_stats(away, league_id, lb_index)
        using_defaults = (src_h == "defaults" or src_a == "defaults")

        # Filter by minimum graded games
        min_game_count = min(graded_h, graded_a)
        if min_game_count < min_graded:
            continue

        game = {
            "vol_a":  vol_a,
            "vol_b":  vol_h,
            "mae_a":  mae_a,
            "mae_b":  mae_h,
            "bias_a": bias_a,
            "bias_b": bias_h,
            "spread": spread,
            "hit_rate_a":    ff_rate_a,
            "hit_rate_b":    ff_rate_h,
            "hit_rate_games_a": ff_total_a,
            "hit_rate_games_b": ff_total_h,
        }

        # Calculate the raw signed average bias for the game (not absolute)
        # If bias is positive, it means ACTUAL > MODEL (model undershoots)
        # Therefore we ADD the raw bias to the model_total to correct it
        avg_bias_raw = (bias_a + bias_h) / 2
        bias_adjusted_total = model_total + avg_bias_raw

        result = compute_confidence(game)
        score  = result["confidence_score"]

        if score < min_score:
            continue

        if hidden_gems:
            # Hidden gems are Moderate/Low games (< 60.0 score) that have High Stability (vol_score >= 15)
            if score >= 60.0 or result["vol_score"] < 15:
                continue

        is_clash = check_clash_profile(home, away, league_id)
        # Fallback to already computed JSON values if manual match failed
        if not is_clash and p.get("is_clash"):
            is_clash = True

        clash_trigger = ""
        if is_clash:
            clash_trigger = p.get("clash_trigger") or ""
            if not clash_trigger:
                mkt_tot = p.get("market_total")
                if mkt_tot is not None and (model_total - mkt_tot) >= 7.0:
                    clash_trigger = "SHARP OVER"
                else:
                    clash_trigger = "CLASH"

        rows.append({
            "league":     league,
            "league_id":  league_id,
            "tier":       tier,
            "home":       home,
            "away":       away,
            "model_total": model_total,
            "bias_adjusted_total": bias_adjusted_total,
            "xpts_h":     xpts_h,
            "xpts_a":     xpts_a,
            "spread":     spread,
            "score":      score,
            "raw":        result["raw_score"],
            "band":       result["band"]["label"],
            "vol_a":      vol_a,
            "vol_h":      vol_h,
            "mae_a":      mae_a,
            "mae_h":      mae_h,
            "bias_a":     bias_a,
            "bias_h":     bias_h,
            "max_vol":    result["max_vol"],
            "max_mae":    result["max_mae"],
            "avg_bias_abs": result["avg_bias_abs"],
            "avg_bias_raw": avg_bias_raw,
            "min_graded_games": min_game_count,
            "vol_score":  result["vol_score"],
            "mae_score":  result["mae_score"],
            "bias_score": result["bias_score"],
            "sprd_score": result["spread_score"],
            "hr_score":   result["hit_rate_score"],
            "weighted_hit_rate": result["weighted_hit_rate"],
            "using_defaults": using_defaults,
            "is_clash": is_clash,
            "clash_trigger": clash_trigger,
        })

    if not rows:
        print(f"\n  No games matched the filters (min_score={min_score}, tier={tier_filter}, league_id={league_id_filter})")
        return

    # Sort by confidence score descending
    rows.sort(key=lambda x: x["score"], reverse=True)

    # ---------------------------------------------------------------------------
    # Print report
    # ---------------------------------------------------------------------------
    print(f"\n{'=' * 120}")
    print(f"  MODEL CONFIDENCE REPORT  |  {date_str}  |  {len(rows)} games")
    print(f"{'=' * 120}")

    if show_components:
        print(f"  {'Score':>6}  {'Band':<11}  {'D':<2}  {'Vol':>5}  {'MAE':>5}  {'Bias':>5}  {'Sprd':>5}  "
              f"{'V':>3}  {'M':>3}  {'B':>3}  {'S':>3}  {'HR':>3}  {'wHR%':>5}  {'xH':>6}  {'xA':>6}  {'Model':>7}  {'TrueTot':>7}  Matchup")
        print(f"  {'-' * 135}")
    else:
        print(f"  {'Score':>6}  {'Band':<11}  {'D':<2}  {'Vol':>5}  {'MAE':>5}  {'Bias':>5}  {'Sprd':>5}  "
              f"{'xH':>6}  {'xA':>6}  {'Model':>7}  {'TrueTot':>7}  Matchup")
        print(f"  {'-' * 110}")

    defaults_count = sum(1 for r in rows if r.get("using_defaults"))

    last_league = None
    for r in rows:
        if r["league"] != last_league:
            print(f"\n  -- {r['league']} ({r['tier']}) --")
            last_league = r["league"]

        band_str = r["band"].strip()
        d_flag   = "~" if r.get("using_defaults") else " "
        whr_str  = f"{r['weighted_hit_rate']*100:.1f}" if r.get("weighted_hit_rate") is not None else "N/A"

        matchup = f"{r['away'][:22]} @ {r['home'][:22]}"
        if r.get("is_clash"):
            if r.get("clash_trigger") == "SHARP OVER":
                matchup += " [CLASH! SHARP OVER]"
            else:
                matchup += " [CLASH]"

        if show_components:
            print(
                f"  {r['score']:>6.1f}  {band_str:<11}  {d_flag:<2}  "
                f"{r['max_vol']:>5.1f}  {r['max_mae']:>5.1f}  {r['avg_bias_raw']:>5.1f}  {r['spread']:>5.1f}  "
                f"{r['vol_score']:>3}  {r['mae_score']:>3}  {r['bias_score']:>3}  {r['sprd_score']:>3}  "
                f"{r['hr_score']:>3}  {whr_str:>5}  "
                f"{r['xpts_h']:>6.1f}  {r['xpts_a']:>6.1f}  {r['model_total']:>7.1f}  {r['bias_adjusted_total']:>7.1f}  "
                f"{matchup}"
            )
        else:
            print(
                f"  {r['score']:>6.1f}  {band_str:<11}  {d_flag:<2}  "
                f"{r['max_vol']:>5.1f}  {r['max_mae']:>5.1f}  {r['avg_bias_raw']:>5.1f}  {r['spread']:>5.1f}  "
                f"{r['xpts_h']:>6.1f}  {r['xpts_a']:>6.1f}  {r['model_total']:>7.1f}  {r['bias_adjusted_total']:>7.1f}  "
                f"{matchup}"
            )

    print(f"\n{'=' * 120}")

    # Summary breakdown by band
    from collections import Counter
    band_counts = Counter(r["band"].strip() for r in rows)
    print(f"\n  SUMMARY")
    print(f"  {'Band':<12}  Games")
    print(f"  {'-' * 25}")
    for band in BAND_ORDER:
        bk = band.strip()
        if bk in band_counts:
            print(f"  {bk:<12}  {band_counts[bk]}")
    print(f"  {'-' * 25}")
    print(f"  {'TOTAL':<12}  {len(rows)}")
    if defaults_count > 0:
        print(f"\n  ~ {defaults_count} game(s) using DEFAULT stats (no league-specific team history)")
        print(f"  ~ These scores may be unreliable. Run aggregate_basketball_stats.py to refresh.")
    print()

    # Top 5 highest confidence
    top5 = rows[:5]
    print(f"  TOP 5 HIGHEST CONFIDENCE:")
    for r in top5:
        matchup = f"{r['away'][:22]} @ {r['home'][:22]}"
        if r.get("is_clash"):
            if r.get("clash_trigger") == "SHARP OVER":
                matchup += " [CLASH! SHARP OVER]"
            else:
                matchup += " [CLASH]"
        print(f"    {r['score']:>5.1f}  {r['band'].strip():<11}  "
              f"{matchup}  |  {r['league']}  "
              f"|  TrueTot:{r['bias_adjusted_total']:.1f}  (Model:{r['model_total']:.1f}  Bias:{r['avg_bias_raw']:+.1f})")
    print()

    return rows


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "date", "confidence_score", "band", "league", "tier", "league_id",
    "away_team", "home_team",
    "model_total", "bias_adjusted_total", "xpts_away", "xpts_home", "spread",
    "vol_away", "vol_home", "mae_away", "mae_home", "bias_away", "bias_home",
    "max_vol", "max_mae", "avg_bias", "min_graded_games",
    "vol_score", "mae_score", "bias_score", "spread_score", "raw_score",
    "is_clash", "clash_trigger"
]

def save_csv(rows: list, date_str: str, suffix: str = "") -> str:
    """
    Write the scored rows to a CSV file.
    Returns the path written.
    """
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    filename = f"confidence_{date_str}{suffix}.csv"
    path = os.path.join(CSV_OUTPUT_DIR, filename)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "date":             date_str,
                "confidence_score": r["score"],
                "band":             r["band"].strip(),
                "league":           r["league"],
                "tier":             r["tier"],
                "league_id":        r["league_id"],
                "away_team":        r["away"],
                "home_team":        r["home"],
                "model_total":      round(r["model_total"], 1),
                "bias_adjusted_total": round(r["bias_adjusted_total"], 1),
                "xpts_away":        round(r["xpts_a"], 1),
                "xpts_home":        round(r["xpts_h"], 1),
                "spread":           round(r["spread"], 1),
                "vol_away":         round(r["vol_a"], 2),
                "vol_home":         round(r["vol_h"], 2),
                "mae_away":         round(r["mae_a"], 2),
                "mae_home":         round(r["mae_h"], 2),
                "bias_away":        round(r["bias_a"], 2),
                "bias_home":        round(r["bias_h"], 2),
                "max_vol":          r["max_vol"],
                "max_mae":          r["max_mae"],
                "avg_bias":         round(r["avg_bias_raw"], 2),
                "min_graded_games": r["min_graded_games"],
                "vol_score":        r["vol_score"],
                "mae_score":        r["mae_score"],
                "bias_score":       r["bias_score"],
                "spread_score":     r["sprd_score"],
                "raw_score":        r["raw"],
                "is_clash":         1 if r.get("is_clash") else 0,
                "clash_trigger":    r.get("clash_trigger", ""),
            })

    return path

def main():
    parser = argparse.ArgumentParser(description="Model Confidence Report for any date's fixtures")
    parser.add_argument("--date",       help="Date YYYY-MM-DD (default: today)")
    parser.add_argument("--min_score",  type=float, default=0.0,
                        help="Only show games with confidence score >= this value (default: 0)")
    parser.add_argument("--tier",       choices=["elite_pro", "top_domestic", "second_division", "lower"],
                        help="Filter by league tier")
    parser.add_argument("--league_id",  type=int, help="Filter to a single league")
    parser.add_argument("--min_graded", type=int, default=0,
                        help="Only show games where BOTH teams have at least this many graded games in the tracking epoch")
    parser.add_argument("--hidden_gems", action="store_true",
                        help="Only show Moderate/Low games with High Stability (Vol Score >= 15)")
    parser.add_argument("--components", action="store_true",
                        help="Show individual score components (vol/mae/bias/spread pts)")
    parser.add_argument("--no_csv",     action="store_true",
                        help="Skip CSV export (console output only)")
    parser.add_argument("--no_playoffs", action="store_true",
                        help="Exclude playoff/post-season games")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    rows = run_report(
        date_str         = date_str,
        min_score        = args.min_score,
        tier_filter      = args.tier,
        league_id_filter = args.league_id,
        show_components  = args.components,
        min_graded       = args.min_graded,
        hidden_gems      = args.hidden_gems,
        no_playoffs      = args.no_playoffs,
    )

    if rows and not args.no_csv:
        # Build suffix from active filters so files don't overwrite each other
        suffix_parts = []
        if args.tier:       suffix_parts.append(args.tier)
        if args.league_id:  suffix_parts.append(f"lid{args.league_id}")
        if args.min_score:  suffix_parts.append(f"min{int(args.min_score)}")
        if args.min_graded: suffix_parts.append(f"graded{args.min_graded}")
        if args.hidden_gems: suffix_parts.append("hidden_gems")
        if args.no_playoffs: suffix_parts.append("no_playoffs")
        suffix = ("_" + "_".join(suffix_parts)) if suffix_parts else ""

        csv_path = save_csv(rows, date_str, suffix=suffix)
        print(f"  CSV saved -> {csv_path}\n")


if __name__ == "__main__":
    main()
