"""
grade_basketball.py
───────────────────
Fetches final scores from api-basketball.com and patches the daily prediction JSON
with actual results (scores, 1X2 outcome). Run once after matches finish.

Usage:
    python grade_basketball.py                    # grades today
    python grade_basketball.py --date 2026-03-20  # grades a specific date
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

API_KEY  = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "basketball")

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
    """Return all finished fixtures for the given date."""
    url = f"{BASE_URL}/games"
    params = {"date": date}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        all_fixtures = r.json().get("response", [])
        # Status "Game Finished" or "Final" or "AOT" (After Over Time)
        finished = [f for f in all_fixtures if f.get("status", {}).get("short") in ("FT", "AOT")]
        return finished
    except Exception as e:
        print(f"  ⚠️  API error: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Grade basketball predictions")
    parser.add_argument("--date",    default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    date = args.date
    print(f"\n{'='*60}")
    print(f"  GRADING BASKETBALL PREDICTIONS | {date}")
    print(f"{'='*60}")

    try:
        data = load_predictions(date)
    except FileNotFoundError as e:
        print(f"  {e}")
        return

    predictions = data.get("predictions", [])
    ungraded = [p for p in predictions if p.get("actual_result") is None]
    print(f"  {len(predictions)} total, {len(ungraded)} ungraded")

    if not ungraded:
        print("  ✅ Already graded.")
        return

    fixtures = fetch_fixtures_for_date(date)
    print(f"  Got {len(fixtures)} finished games from API")

    if not fixtures: return

    # Map (league_id, home, away) -> (home_score, away_score)
    results_map = {}
    for fix in fixtures:
        lid = fix["league"]["id"]
        h_name = fix["teams"]["home"]["name"]
        a_name = fix["teams"]["away"]["name"]
        h_score = fix.get("scores", {}).get("home", {}).get("total")
        a_score = fix.get("scores", {}).get("away", {}).get("total")
        if h_score is not None and a_score is not None:
            results_map[(lid, h_name, a_name)] = (int(h_score), int(a_score))

    matched = 0
    graded_list = []
    wins = 0
    total = 0

    for pred in predictions:
        if pred.get("actual_result"):
            graded_list.append(pred)
            continue
        
        key = (pred["league_id"], pred["home_team"], pred["away_team"])
        if key in results_map:
            h_s, a_s = results_map[key]
            actual = "HOME" if h_s > a_s else "AWAY"
            
            p = pred.copy()
            p["actual_home_score"] = h_s
            p["actual_away_score"] = a_s
            p["actual_result"]     = actual
            
            # Outcome grade
            is_win = (p.get("predicted_result") == actual)
            if is_win: wins += 1
            total += 1
            
            print(f"  [OK] {pred['home_team']} {h_s}-{a_s} {pred['away_team']} -> {actual} ({'WIN' if is_win else 'LOSS'})")
            graded_list.append(p)
            matched += 1
        else:
            graded_list.append(pred)

    print(f"\n  Matched: {matched} | Accuracy: {wins}/{total}" + (f" ({100*wins//total}%)" if total else ""))

    if not args.dry_run:
        data["predictions"] = graded_list
        data["graded_at"] = datetime.now().isoformat()
        data["grade_summary"] = {"wins": wins, "total": total, "pct": round(100*wins/total,1) if total else 0}
        save_predictions(date, data)

if __name__ == "__main__":
    main()
