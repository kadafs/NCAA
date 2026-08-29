"""
grade_football.py
─────────────────
Fetches final scores from the API and patches the daily prediction JSON
with actual results (goals, BTTS, 1X2 outcome). Run once after matches finish.

Usage:
    python grade_football.py                    # grades today
    python grade_football.py --date 2026-03-15  # grades a specific date
    python grade_football.py --date 2026-03-15 --dry-run  # preview only
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

API_KEY  = os.getenv("API_BASKETBALL_KEY")   # same key covers api-sports football
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "football")


# ── Helpers ──────────────────────────────────────────────────────────────────

def predictions_path(date: str) -> str:
    return os.path.join(DATA_DIR, f"universal_predictions_{date}.json")


def load_predictions(date: str) -> dict:
    path = predictions_path(date)
    if not os.path.exists(path):
        raise FileNotFoundError(f"No prediction file for {date}: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_predictions(date: str, data: dict) -> None:
    path = predictions_path(date)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved → {path}")


def fetch_fixtures_for_date(date: str) -> list:
    """Return all finished fixtures for the given date from api-sports.io."""
    url = f"{BASE_URL}/fixtures"
    params = {"date": date}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        all_fixtures = r.json().get("response", [])
        # Filter to only finished games (FT, AET, PEN)
        finished = [f for f in all_fixtures
                    if f.get("fixture", {}).get("status", {}).get("short") in ("FT", "AET", "PEN")]
        return finished
    except Exception as e:
        print(f"  ⚠️  API error fetching fixtures: {e}")
        return []


def build_result_key(fixture: dict) -> tuple:
    """Return (league_id, home_team_name, away_team_name) for matching."""
    league_id  = fixture["league"]["id"]
    home_team  = fixture["teams"]["home"]["name"]
    away_team  = fixture["teams"]["away"]["name"]
    return (league_id, home_team, away_team)


def grade_prediction(pred: dict, home_goals: int, away_goals: int) -> dict:
    """Populate actual_* fields on a prediction dict and return it updated."""
    actual_result = (
        "HOME" if home_goals > away_goals else
        "AWAY" if away_goals > home_goals else
        "DRAW"
    )
    actual_btts = home_goals > 0 and away_goals > 0

    p = pred.copy()
    p["actual_home_goals"] = home_goals
    p["actual_away_goals"] = away_goals
    p["actual_btts"]       = actual_btts
    p["actual_draw"]       = (actual_result == "DRAW")
    p["actual_result"]     = actual_result
    
    # Delta Grading Matrix
    actual_total = home_goals + away_goals
    xg_total = p.get("xg_total")
    if xg_total is not None:
        delta = abs(actual_total - xg_total)
        signed_delta = actual_total - xg_total
        
        if delta <= 0.50: tier = "🎯 BULLSEYE"
        elif delta <= 1.00: tier = "🟢 EXCELLENT"
        elif delta <= 1.50: tier = "🟡 SOLID"
        elif delta <= 2.00: tier = "🟠 MISS"
        else: tier = "🔴 BUST"
        
        p["total_delta"] = round(delta, 2)
        p["signed_delta"] = round(signed_delta, 2)
        p["accuracy_tier"] = tier

    return p


def btts_grade(pred: dict) -> str | None:
    """Return WIN, LOSS, or None (for PASS) based on BTTS decision vs actual."""
    decision = pred.get("btts_decision")
    actual   = pred.get("actual_btts")
    if decision == "PASS" or actual is None:
        return None
    if decision == "PLAY YES":
        return "WIN" if actual else "LOSS"
    if decision == "PLAY NO":
        return "WIN" if not actual else "LOSS"
    return None


def outcome_grade(pred: dict) -> str | None:
    """Return WIN or LOSS for 1X2 prediction vs actual."""
    pred_result   = pred.get("predicted_result")
    actual_result = pred.get("actual_result")
    if not pred_result or not actual_result:
        return None
    return "WIN" if pred_result == actual_result else "LOSS"


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Grade football predictions against actual results")
    parser.add_argument("--date",    default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    args = parser.parse_args()

    date = args.date
    print(f"\n{'='*60}")
    print(f"  GRADING FOOTBALL PREDICTIONS | {date}")
    print(f"{'='*60}")

    # Load predictions
    data = load_predictions(date)
    predictions = data["predictions"]
    ungraded = [p for p in predictions if p.get("actual_result") is None]
    print(f"  {len(predictions)} total predictions, {len(ungraded)} ungraded")

    if not ungraded:
        print("  ✅ All predictions already graded.")
        return

    # Fetch actual results from API
    print(f"  Fetching final scores from API for {date}...")
    fixtures = fetch_fixtures_for_date(date)
    print(f"  Got {len(fixtures)} finished fixtures")

    if not fixtures:
        print("  ⚠️  No finished fixtures returned — try again later or check API key.")
        return

    # Build lookup: (league_id, home_name, away_name) → (home_goals, away_goals)
    results_map: dict[tuple, tuple[int, int]] = {}
    for fix in fixtures:
        key = build_result_key(fix)
        home_goals = fix["goals"]["home"]
        away_goals = fix["goals"]["away"]
        if home_goals is not None and away_goals is not None:
            results_map[key] = (int(home_goals), int(away_goals))

    # Grade each prediction
    matched = 0
    missed  = 0
    graded_predictions = []

    for pred in predictions:
        # Skip already graded
        if pred.get("actual_result") is not None:
            graded_predictions.append(pred)
            continue

        key = (pred["league_id"], pred["home_team"], pred["away_team"])
        if key in results_map:
            home_goals, away_goals = results_map[key]
            graded = grade_prediction(pred, home_goals, away_goals)
            graded_predictions.append(graded)
            matched += 1

            o_grade = outcome_grade(graded)
            b_grade = btts_grade(graded)
            tier_str = graded.get("accuracy_tier", "")
            score_str   = f"{home_goals}-{away_goals}"
            outcome_str = f"  1X2: {graded['predicted_result']} -> {graded['actual_result']} [{o_grade}]"
            btts_str    = f"  BTTS: {graded['btts_decision']} [{b_grade}]" if b_grade else ""
            
            print(f"  [OK] {pred['home_team']} {score_str} {pred['away_team']}  {outcome_str}{btts_str} | {tier_str}")
        else:
            graded_predictions.append(pred)
            missed += 1
            if missed <= 5:  # only show first few misses
                print(f"  [X] No match found: {pred['home_team']} vs {pred['away_team']} (league {pred['league_id']})")

    if missed > 5:
        print(f"     ... and {missed - 5} more unmatched games")

    # Summary
    print(f"\n  Matched: {matched}  |  Not found: {missed}")

    # Compute grade summary
    completed = [p for p in graded_predictions if p.get("actual_result")]
    
    # Only grade 1X2 for matches that meet the 60% premium filter (PLAY or STRONG PLAY)
    x12_played = [
        p for p in completed
        if "PLAY" in p.get("outcome_decision", "") 
        or max(p.get("home_win_prob", 0), p.get("away_win_prob", 0), p.get("draw_prob_1x2", 0)) >= 60.0
    ]
    x12_results = [(outcome_grade(p), p) for p in x12_played]
    x12_wins  = sum(1 for g, _ in x12_results if g == "WIN")
    x12_total = sum(1 for g, _ in x12_results if g is not None)

    # Only grade BTTS for matches that meet the 70% premium filter
    btts_played = [
        p for p in completed 
        if p.get("btts_decision") in ("PLAY YES", "[STRONG] PLAY YES") 
        and p.get("btts_prob", 0) >= 70.0
    ]
    btts_wins   = sum(1 for p in btts_played if btts_grade(p) == "WIN")
    btts_total  = len(btts_played)

    print(f"\n  [---] Grade Summary ({date})")
    print(f"     1X2:  {x12_wins}/{x12_total} correct" + (f"  ({100*x12_wins//x12_total}%)" if x12_total else ""))
    print(f"     BTTS YES: {btts_wins}/{btts_total} wins"  + (f"  ({100*btts_wins//btts_total}%)" if btts_total else ""))

    if args.dry_run:
        print("\n  [DRY RUN] — no changes saved.")
        return

    data["predictions"]    = graded_predictions
    data["graded_at"]      = datetime.now().isoformat()
    data["grade_summary"]  = {
        "outcome_wins":  x12_wins,
        "outcome_total": x12_total,
        "outcome_pct":   round(100 * x12_wins / x12_total, 1) if x12_total else None,
        "btts_wins":     btts_wins,
        "btts_total":    btts_total,
        "btts_pct":      round(100 * btts_wins / btts_total, 1) if btts_total else None,
    }
    save_predictions(date, data)
    print("\n  ✅ Grading complete!")


if __name__ == "__main__":
    main()
