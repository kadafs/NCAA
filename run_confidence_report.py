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
      2. Fuzzy name match (≥ 0.80 similarity) within same league_id
      3. Fuzzy name match across any league (last resort)
    """
    name_lower = name.lower().strip()

    # 1. Exact match in league
    if (name_lower, league_id) in index:
        return index[(name_lower, league_id)]

    # 2. Fuzzy match in league
    league_names = [(k[0], k[1]) for k in index if k[1] == league_id]
    if league_names:
        names_only = [k[0] for k in league_names]
        matches = difflib.get_close_matches(name_lower, names_only, n=1, cutoff=0.80)
        if matches:
            return index[(matches[0], league_id)]

    # 3. Fuzzy match across all leagues
    all_names = [k[0] for k in index]
    matches = difflib.get_close_matches(name_lower, all_names, n=1, cutoff=0.80)
    if matches:
        # pick entry with highest graded_totals if multiple leagues have this name
        candidates = [v for k, v in index.items() if k[0] == matches[0]]
        candidates.sort(key=lambda x: x.get("graded_totals", 0), reverse=True)
        return candidates[0] if candidates else None

    return None


def get_team_stats(name: str, league_id: int, index: dict) -> tuple[float, float]:
    """
    Returns (mae, bias) for a team from the leaderboard.
    Falls back to defaults when team is not found.
    """
    entry = lookup_team(name, league_id, index)
    if entry:
        mae  = entry.get("mae",               DEFAULT_MAE)
        bias = entry.get("avg_signed_delta",  DEFAULT_BIAS)
        # Use ADV stats if available, fall back to base stats
        adv = entry.get("adv")
        if adv and isinstance(adv, dict):
            mae  = adv.get("mae",              mae)
            bias = adv.get("avg_signed_delta", bias)
        return float(mae or DEFAULT_MAE), float(bias or DEFAULT_BIAS)
    return DEFAULT_MAE, DEFAULT_BIAS


# ---------------------------------------------------------------------------
# Band label helpers (ASCII-safe)
# ---------------------------------------------------------------------------

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
               league_id_filter: int = None, show_components: bool = False):

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

        # Spread from projected pts
        spread = abs((xpts_h or 0) - (xpts_a or 0))

        # Volatility — already in the prediction JSON
        vol_h = p.get("home_team_volatility") or DEFAULT_MAE
        vol_a = p.get("away_team_volatility") or DEFAULT_MAE

        # MAE + Bias — from leaderboard
        mae_h, bias_h = get_team_stats(home, league_id, lb_index)
        mae_a, bias_a = get_team_stats(away, league_id, lb_index)

        game = {
            "vol_a":  vol_a,
            "vol_b":  vol_h,
            "mae_a":  mae_a,
            "mae_b":  mae_h,
            "bias_a": bias_a,
            "bias_b": bias_h,
            "spread": spread,
        }

        result = compute_confidence(game)
        score  = result["confidence_score"]

        if score < min_score:
            continue

        rows.append({
            "league":     league,
            "league_id":  league_id,
            "tier":       tier,
            "home":       home,
            "away":       away,
            "model_total": model_total,
            "xpts_h":     xpts_h,
            "xpts_a":     xpts_a,
            "spread":     spread,
            "score":      score,
            "raw":        result["raw_score"],
            "band":       result["band"]["label"],
            "avg_vol":    result["avg_vol"],
            "avg_mae":    result["avg_mae"],
            "avg_bias":   result["avg_bias_abs"],
            "vol_score":  result["vol_score"],
            "mae_score":  result["mae_score"],
            "bias_score": result["bias_score"],
            "sprd_score": result["spread_score"],
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
        print(f"  {'Score':>6}  {'Band':<11}  {'Vol':>5}  {'MAE':>5}  {'Bias':>5}  {'Sprd':>5}  "
              f"{'V':>3}  {'M':>3}  {'B':>3}  {'S':>3}  {'xH':>6}  {'xA':>6}  {'Model':>7}  Matchup")
        print(f"  {'-' * 110}")
    else:
        print(f"  {'Score':>6}  {'Band':<11}  {'Vol':>5}  {'MAE':>5}  {'Bias':>5}  {'Sprd':>5}  "
              f"{'xH':>6}  {'xA':>6}  {'Model':>7}  Matchup")
        print(f"  {'-' * 96}")

    last_league = None
    for r in rows:
        if r["league"] != last_league:
            print(f"\n  -- {r['league']} ({r['tier']}) --")
            last_league = r["league"]

        band_str = r["band"].strip()

        if show_components:
            print(
                f"  {r['score']:>6.1f}  {band_str:<11}  "
                f"{r['avg_vol']:>5.1f}  {r['avg_mae']:>5.1f}  {r['avg_bias']:>5.1f}  {r['spread']:>5.1f}  "
                f"{r['vol_score']:>3}  {r['mae_score']:>3}  {r['bias_score']:>3}  {r['sprd_score']:>3}  "
                f"{r['xpts_h']:>6.1f}  {r['xpts_a']:>6.1f}  {r['model_total']:>7.1f}  "
                f"{r['away'][:22]} @ {r['home'][:22]}"
            )
        else:
            print(
                f"  {r['score']:>6.1f}  {band_str:<11}  "
                f"{r['avg_vol']:>5.1f}  {r['avg_mae']:>5.1f}  {r['avg_bias']:>5.1f}  {r['spread']:>5.1f}  "
                f"{r['xpts_h']:>6.1f}  {r['xpts_a']:>6.1f}  {r['model_total']:>7.1f}  "
                f"{r['away'][:22]} @ {r['home'][:22]}"
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
    print()

    # Top 5 highest confidence
    top5 = rows[:5]
    print(f"  TOP 5 HIGHEST CONFIDENCE:")
    for r in top5:
        print(f"    {r['score']:>5.1f}  {r['band'].strip():<11}  "
              f"{r['away'][:22]} @ {r['home'][:22]}  |  {r['league']}  "
              f"|  Model:{r['model_total']:.1f}  xH:{r['xpts_h']:.1f}  xA:{r['xpts_a']:.1f}")
    print()

    return rows


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "date", "confidence_score", "band", "league", "tier", "league_id",
    "away_team", "home_team",
    "model_total", "xpts_away", "xpts_home", "spread",
    "avg_vol", "avg_mae", "avg_bias",
    "vol_score", "mae_score", "bias_score", "spread_score", "raw_score",
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
                "xpts_away":        round(r["xpts_a"], 1),
                "xpts_home":        round(r["xpts_h"], 1),
                "spread":           round(r["spread"], 1),
                "avg_vol":          r["avg_vol"],
                "avg_mae":          r["avg_mae"],
                "avg_bias":         r["avg_bias"],
                "vol_score":        r["vol_score"],
                "mae_score":        r["mae_score"],
                "bias_score":       r["bias_score"],
                "spread_score":     r["sprd_score"],
                "raw_score":        r["raw"],
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
    parser.add_argument("--components", action="store_true",
                        help="Show individual score components (vol/mae/bias/spread pts)")
    parser.add_argument("--no_csv",     action="store_true",
                        help="Skip CSV export (console output only)")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    rows = run_report(
        date_str         = date_str,
        min_score        = args.min_score,
        tier_filter      = args.tier,
        league_id_filter = args.league_id,
        show_components  = args.components,
    )

    if rows and not args.no_csv:
        # Build suffix from active filters so files don't overwrite each other
        suffix_parts = []
        if args.tier:       suffix_parts.append(args.tier)
        if args.league_id:  suffix_parts.append(f"lid{args.league_id}")
        if args.min_score:  suffix_parts.append(f"min{int(args.min_score)}")
        suffix = ("_" + "_".join(suffix_parts)) if suffix_parts else ""

        csv_path = save_csv(rows, date_str, suffix=suffix)
        print(f"  CSV saved -> {csv_path}\n")


if __name__ == "__main__":
    main()
