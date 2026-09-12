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
from datetime import datetime, timedelta
from core.xgot_engine import compute_match_xgot

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


def fetch_fixture_statistics(fixture_id: int, home_team_id: int = None, away_team_id: int = None) -> dict:
    """
    Fetch statistics for a single fixture.
    Returns a dict with:
    {
        "corners": int,
        "booking_pts": int,
        "home": dict,
        "away": dict
    }
    or None if unavailable.
    """
    url = f"{BASE_URL}/fixtures/statistics"
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        stats_response = r.json().get("response", [])
        
        if not stats_response:
            return None
            
        total_corners = 0
        total_booking_pts = 0
        
        def parse_team_stats(stats_list):
            d = {
                "shots_on_goal": 0,
                "total_shots": 0,
                "shots_insidebox": 0,
                "shots_outsidebox": 0,
                "saves": 0,
                "xg": None
            }
            for s in stats_list:
                t = s.get("type")
                val = s.get("value")
                if val is None:
                    continue
                if isinstance(val, str):
                    val = val.replace("%", "").strip()
                try:
                    num = float(val) if "." in str(val) else int(val)
                except Exception:
                    num = 0
                    
                if t == "Shots on Goal": d["shots_on_goal"] = int(num)
                elif t == "Total Shots": d["total_shots"] = int(num)
                elif t == "Shots insidebox": d["shots_insidebox"] = int(num)
                elif t == "Shots outsidebox": d["shots_outsidebox"] = int(num)
                elif t == "Goalkeeper Saves": d["saves"] = int(num)
                elif t == "expected_goals": d["xg"] = float(num)
            return d

        home_stats = parse_team_stats([])
        away_stats = parse_team_stats([])

        if len(stats_response) >= 2:
            t0_id = stats_response[0].get("team", {}).get("id")
            t1_id = stats_response[1].get("team", {}).get("id")
            if home_team_id and t1_id == home_team_id:
                home_stats = parse_team_stats(stats_response[1].get("statistics", []))
                away_stats = parse_team_stats(stats_response[0].get("statistics", []))
            else:
                home_stats = parse_team_stats(stats_response[0].get("statistics", []))
                away_stats = parse_team_stats(stats_response[1].get("statistics", []))
        elif len(stats_response) == 1:
            home_stats = parse_team_stats(stats_response[0].get("statistics", []))

        for team_stats in stats_response:
            stats = team_stats.get("statistics", [])
            for stat in stats:
                val = stat.get("value")
                if val is None:
                    continue
                if stat.get("type") == "Corner Kicks":
                    try: total_corners += int(val)
                    except: pass
                elif stat.get("type") == "Yellow Cards":
                    try: total_booking_pts += int(val) * 10
                    except: pass
                elif stat.get("type") == "Red Cards":
                    try: total_booking_pts += int(val) * 25
                    except: pass
                    
        return {
            "corners": total_corners,
            "booking_pts": total_booking_pts,
            "home": home_stats,
            "away": away_stats
        }
    except Exception as e:
        return None


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

    # Corners & booking grading — populated later from fixtures/statistics
    # (These are set by grade_corners_from_api if available)
    # p["actual_corners_total"] = None  -- set externally
    # p["actual_booking_pts"]   = None  -- set externally
    
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


def corner_grade(pred: dict) -> str | None:
    """Return WIN, LOSS, or None (PASS) based on corner_call vs actual corners."""
    corners = pred.get("corners") or {}
    call = corners.get("corner_call")
    if not call or call == "PASS":
        return None
    actual_total = pred.get("actual_corners_total")
    if actual_total is None:
        return None
    line_str = corners.get("corner_call_line", "")
    # Parse the line number from e.g. "OVER 9.5" or "UNDER 9.5"
    try:
        line_val = float(line_str.split()[-1])
    except (ValueError, IndexError):
        return None
    if "OVER" in line_str:
        return "WIN" if actual_total > line_val else "LOSS"
    elif "UNDER" in line_str:
        return "WIN" if actual_total < line_val else "LOSS"
    return None


def booking_grade(pred: dict) -> str | None:
    """Return WIN, LOSS, or None (PASS) based on booking_call vs actual booking pts."""
    corners = pred.get("corners") or {}
    call = corners.get("booking_call")
    if not call or call == "PASS":
        return None
    actual_pts = pred.get("actual_booking_pts")
    if actual_pts is None:
        return None
    line_str = corners.get("booking_call_line", "")
    try:
        line_val = float(line_str.split()[-2])  # e.g. "OVER 30 PTS" -> 30
    except (ValueError, IndexError):
        return None
    if "OVER" in line_str:
        return "WIN" if actual_pts > line_val else "LOSS"
    elif "UNDER" in line_str:
        return "WIN" if actual_pts < line_val else "LOSS"
    return None


def outcome_grade(pred: dict) -> str | None:
    """Return WIN or LOSS for 1X2 prediction vs actual."""
    pred_result   = pred.get("predicted_result")
    actual_result = pred.get("actual_result")
    if not pred_result or not actual_result:
        return None
    return "WIN" if pred_result == actual_result else "LOSS"


def resolve_target_date(date_arg: str | None = None) -> str:
    if date_arg:
        return date_arg
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    # If today's predictions file doesn't exist, check yesterday
    if not os.path.exists(predictions_path(today_str)):
        if os.path.exists(predictions_path(yesterday_str)):
            print(f"  [Auto-Date] Today's file ({today_str}) not found. Defaulting to yesterday ({yesterday_str}).")
            return yesterday_str
    # If running in early morning (hours 0-6) and yesterday's file has ungraded predictions
    elif now.hour < 6 and os.path.exists(predictions_path(yesterday_str)):
        try:
            with open(predictions_path(yesterday_str), encoding="utf-8") as f:
                ydata = json.load(f)
            if any(p.get("actual_result") is None for p in ydata.get("predictions", [])):
                print(f"  [Auto-Date] Early morning run ({now.hour:02d}:00) and yesterday ({yesterday_str}) has ungraded games. Defaulting to yesterday.")
                return yesterday_str
        except Exception:
            pass
    return today_str


# ── Main ─────────────────────────────────────────────────────────────────────

def compute_grade_summary(predictions: list) -> dict:
    """Compute 1X2, BTTS, Corners, and Booking accuracy metrics from graded predictions."""
    completed = [p for p in predictions if p.get("actual_result")]
    
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
    
    # Grade corners (only count PASS-filtered calls)
    corners_played = [p for p in completed if (p.get("corners") or {}).get("corner_call") not in (None, "PASS")]
    corners_wins  = sum(1 for p in corners_played if corner_grade(p) == "WIN")
    corners_total = sum(1 for p in corners_played if corner_grade(p) is not None)

    # Grade bookings (only count PASS-filtered calls)
    booking_played = [p for p in completed if (p.get("corners") or {}).get("booking_call") not in (None, "PASS")]
    booking_wins  = sum(1 for p in booking_played if booking_grade(p) == "WIN")
    booking_total = sum(1 for p in booking_played if booking_grade(p) is not None)

    return {
        "outcome_wins":  x12_wins,
        "outcome_total": x12_total,
        "outcome_pct":   round(100 * x12_wins / x12_total, 1) if x12_total else None,
        "btts_wins":     btts_wins,
        "btts_total":    btts_total,
        "btts_pct":      round(100 * btts_wins / btts_total, 1) if btts_total else None,
        "corners_wins":  corners_wins,
        "corners_total": corners_total,
        "corners_pct":   round(100 * corners_wins / corners_total, 1) if corners_total else None,
        "booking_wins":  booking_wins,
        "booking_total": booking_total,
        "booking_pct":   round(100 * booking_wins / booking_total, 1) if booking_total else None,
    }


def grade_football_date(date: str, dry_run: bool = False, force: bool = False) -> dict | None:
    """Grade predictions for a specific date against actual match results from API."""
    print(f"\n{'='*60}")
    print(f"  GRADING FOOTBALL PREDICTIONS | {date}")
    print(f"{'='*60}")

    # Load predictions
    try:
        data = load_predictions(date)
    except FileNotFoundError as e:
        print(f"  ⚠️ {e}")
        return None
    predictions = data.get("predictions", [])
    ungraded = [p for p in predictions if p.get("actual_result") is None]
    print(f"  {len(predictions)} total predictions, {len(ungraded)} ungraded")

    if not ungraded and not force:
        print("  ✅ All predictions already graded.")
        summary = data.get("grade_summary")
        if not summary:
            summary = compute_grade_summary(predictions)
            data["grade_summary"] = summary
            if not dry_run:
                save_predictions(date, data)
                print(f"  ✅ Saved missing grade_summary for {date}!")
        return summary

    # Fetch actual results from API
    print(f"  Fetching final scores from API for {date}...")
    fixtures = fetch_fixtures_for_date(date)
    print(f"  Got {len(fixtures)} finished fixtures")

    if not fixtures:
        print("  ⚠️  No finished fixtures returned — try again later or check API key.")
        return None

    # Build lookup: (league_id, home_name, away_name) → (home_goals, away_goals, fixture_id)
    results_map: dict[tuple, tuple[int, int, int]] = {}
    for fix in fixtures:
        key = build_result_key(fix)
        home_goals = fix["goals"]["home"]
        away_goals = fix["goals"]["away"]
        fixture_id = fix["fixture"]["id"]
        if home_goals is not None and away_goals is not None:
            results_map[key] = (int(home_goals), int(away_goals), fixture_id)

    # Grade each prediction
    matched = 0
    missed  = 0
    graded_predictions = []

    for pred in predictions:
        # Skip already graded (but fetch stats if missing)
        if pred.get("actual_result") is not None:
            corners_block = pred.get("corners") or {}
            corner_call   = corners_block.get("corner_call")
            booking_call  = corners_block.get("booking_call")
            needs_stats   = (corner_call and corner_call != "PASS") or (booking_call and booking_call != "PASS")
            if needs_stats and (pred.get("actual_corners_total") is None or pred.get("actual_booking_pts") is None):
                key = (pred["league_id"], pred["home_team"], pred["away_team"])
                if key in results_map:
                    _, _, fixture_id = results_map[key]
                    h_id = pred.get("home_team_id")
                    a_id = pred.get("away_team_id")
                    stats = fetch_fixture_statistics(fixture_id, h_id, a_id)
                    if stats:
                        pred["actual_corners_total"] = stats["corners"]
                        pred["actual_booking_pts"]   = stats["booking_pts"]
                        if not pred.get("post_match_xgot"):
                            h_goals = pred.get("actual_home_goals", 0)
                            a_goals = pred.get("actual_away_goals", 0)
                            pred["post_match_xgot"] = compute_match_xgot(
                                home_stats=stats.get("home"),
                                away_stats=stats.get("away"),
                                goals_h=h_goals,
                                goals_a=a_goals,
                                pre_xg_home=pred.get("xg_home"),
                                pre_xg_away=pred.get("xg_away")
                            )
                        time.sleep(0.05)
            graded_predictions.append(pred)
            continue

        key = (pred["league_id"], pred["home_team"], pred["away_team"])
        if key in results_map:
            home_goals, away_goals, fixture_id = results_map[key]
            graded = grade_prediction(pred, home_goals, away_goals)
            
            # --- Fetch statistics if this is a Corners/Booking YES/NO call ---
            corners_block = graded.get("corners") or {}
            corner_call = corners_block.get("corner_call")
            booking_call = corners_block.get("booking_call")
            
            h_id = pred.get("home_team_id")
            a_id = pred.get("away_team_id")
            stats = fetch_fixture_statistics(fixture_id, h_id, a_id)
            if stats:
                graded["actual_corners_total"] = stats["corners"]
                graded["actual_booking_pts"]   = stats["booking_pts"]
                xgot_data = compute_match_xgot(
                    home_stats=stats.get("home"),
                    away_stats=stats.get("away"),
                    goals_h=home_goals,
                    goals_a=away_goals,
                    pre_xg_home=pred.get("xg_home"),
                    pre_xg_away=pred.get("xg_away")
                )
                graded["post_match_xgot"] = xgot_data
                time.sleep(0.05)
            else:
                graded["actual_corners_total"] = None
                graded["actual_booking_pts"]   = None
                # Fallback calculation from pre-match xG and actual goals
                graded["post_match_xgot"] = compute_match_xgot(
                    home_stats={},
                    away_stats={},
                    goals_h=home_goals,
                    goals_a=away_goals,
                    pre_xg_home=pred.get("xg_home"),
                    pre_xg_away=pred.get("xg_away")
                )

            graded_predictions.append(graded)
            matched += 1

            o_grade = outcome_grade(graded)
            b_grade = btts_grade(graded)
            tier_str = graded.get("accuracy_tier", "")
            score_str   = f"{home_goals}-{away_goals}"
            outcome_str = f"  1X2: {graded['predicted_result']} -> {graded['actual_result']} [{o_grade}]"
            btts_str    = f"  BTTS: {graded['btts_decision']} [{b_grade}]" if b_grade else ""
            
            c_grade = corner_grade(graded)
            bk_grade = booking_grade(graded)
            corners_block = graded.get("corners") or {}
            corner_str = f"  CORNERS: {corners_block.get('corner_call_line','?')} [{c_grade}]" if c_grade else ""
            booking_str = f"  BOOKING: {corners_block.get('booking_call_line','?')} [{bk_grade}]" if bk_grade else ""
            print(f"  [OK] {pred['home_team']} {score_str} {pred['away_team']}  {outcome_str}{btts_str}{corner_str}{booking_str} | {tier_str}")
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
    summary = compute_grade_summary(graded_predictions)

    print(f"\n  [---] Grade Summary ({date})")
    x12_w = summary["outcome_wins"]
    x12_t = summary["outcome_total"]
    btts_w = summary["btts_wins"]
    btts_t = summary["btts_total"]
    corn_w = summary["corners_wins"]
    corn_t = summary["corners_total"]
    book_w = summary["booking_wins"]
    book_t = summary["booking_total"]

    print(f"     1X2:  {x12_w}/{x12_t} correct" + (f"  ({summary['outcome_pct']}%)" if summary['outcome_pct'] is not None else ""))
    print(f"     BTTS YES: {btts_w}/{btts_t} wins"  + (f"  ({summary['btts_pct']}%)" if summary['btts_pct'] is not None else ""))
    if corn_t:
        print(f"     CORNERS:  {corn_w}/{corn_t} wins" + (f"  ({summary['corners_pct']}%)" if summary['corners_pct'] is not None else ""))
    if book_t:
        print(f"     BOOKINGS: {book_w}/{book_t} wins" + (f"  ({summary['booking_pct']}%)" if summary['booking_pct'] is not None else ""))

    if dry_run:
        print("\n  [DRY RUN] — no changes saved.")
        return summary

    data["predictions"]    = graded_predictions
    data["graded_at"]      = datetime.now().isoformat()
    data["grade_summary"]  = summary
    save_predictions(date, data)
    print("\n  ✅ Grading complete!")

    # Auto-update historical league and team leaderboards
    try:
        import aggregate_league_stats
        aggregate_league_stats.main(args_list=[])
    except Exception as e:
        print(f"  ⚠️ Note: Could not auto-update leaderboards: {e}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Grade football predictions against actual results")
    parser.add_argument("--date",    default=None, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    parser.add_argument("--force",   action="store_true", help="Force re-grading / updating summary even if graded")
    args = parser.parse_args()

    date = resolve_target_date(args.date)
    grade_football_date(date, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
