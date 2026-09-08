"""
grade_basketball_v2.py
───────────────────
Fetches final scores from api-basketball.com and patches the daily V2 prediction JSON
with actual results (scores, 1X2 outcome). Run once after matches finish.

Usage:
    python grade_basketball_v2.py                    # grades today
    python grade_basketball_v2.py --date 2026-03-20  # grades a specific date
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
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
    clean_date = date.replace("_v2", "")
    return os.path.join(DATA_DIR, f"universal_predictions_{clean_date}_v2.json")

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
        finished = [f for f in all_fixtures if f.get("status", {}).get("short") in ("FT", "AOT")]
        return finished
    except Exception as e:
        print(f"  [!] API error: {e}")
        return []


def _normalize_name(name: str) -> str:
    """Lowercase + strip common suffixes for fuzzy team matching."""
    import re
    name = name.lower().strip()
    name = re.sub(r'\b(bc|bk|basketball|club|sporting|fc|ac|sc)\b', '', name)
    return re.sub(r'\s+', ' ', name).strip()


def _delta_tier(delta: float) -> str:
    """Return ASCII accuracy tier string for a given absolute delta."""
    if delta <= 4.0:    return "BULLSEYE"
    elif delta <= 8.5:  return "EXCELLENT"
    elif delta <= 14.5: return "SOLID"
    elif delta <= 21.0: return "MISS"
    else:               return "BUST"

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


def main():
    parser = argparse.ArgumentParser(description="Grade basketball predictions")
    parser.add_argument("--date",    default=None, help="Date to grade (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--regrade", action="store_true",
                        help="Recalculate Delta Matrix fields on already-graded games (no API call needed)")
    args = parser.parse_args()

    date = resolve_target_date(args.date)
    print(f"\n{'='*60}")
    print(f"  GRADING BASKETBALL PREDICTIONS | {date}")
    print(f"{'='*60}")

    try:
        data = load_predictions(date)
    except FileNotFoundError as e:
        print(f"  {e}")
        return

    predictions = data.get("predictions", [])
    ungraded = [p for p in predictions if p.get("actual_result") is None and not p.get("awarded_match")]
    missing_delta = [
        p for p in predictions
        if p.get("actual_result")
        and p.get("accuracy_tier") is None
        and (p.get("model", {}).get("total") or p.get("model_total"))
    ]
    print(f"  {len(predictions)} total, {len(ungraded)} ungraded, {len(missing_delta)} graded but missing Delta fields")

    # --regrade: recalculate Delta fields on already-stored scores, no API call
    if args.regrade:
        if not missing_delta:
            print("  ✅ All graded games already have Delta fields.")
            return
        print(f"  🔄 Regrading {len(missing_delta)} games with Delta Matrix (using stored scores)...")
        graded_list = []
        patched = 0
        wins_by_model  = {}
        total_by_model = {}
        for pred in predictions:
            if pred.get("actual_result") and pred.get("accuracy_tier") is None:
                p = pred.copy()
                h_s = p.get("actual_home_score")
                a_s = p.get("actual_away_score")
                status = p.get("status", "FT")
                model_total = p.get("model", {}).get("total") or p.get("model_total")
                mdl = p.get("model_architecture", "[  SRS   ]")
                if h_s is not None and a_s is not None and model_total:
                    if status == "AOT":
                        p["accuracy_tier"] = "OT WARP"
                        p["total_delta"] = None
                        p["total_rpe"] = None
                    else:
                        actual_total = h_s + a_s
                        delta = abs(actual_total - model_total)
                        signed_delta = actual_total - model_total
                        rpe = (delta / actual_total) * 100 if actual_total > 0 else 0
                        p["total_delta"] = round(delta, 2)
                        p["signed_delta"] = round(signed_delta, 2)
                        p["total_rpe"] = round(rpe, 2)
                        p["accuracy_tier"] = _delta_tier(delta)
                    # Per-model outcome tracking
                    is_win = p.get("predicted_result") == p.get("actual_result")
                    wins_by_model[mdl]  = wins_by_model.get(mdl, 0)  + (1 if is_win else 0)
                    total_by_model[mdl] = total_by_model.get(mdl, 0) + 1
                    print(f"  [REGRADE] {pred['home_team']} vs {pred['away_team']} ({mdl.strip()}) → {p.get('accuracy_tier')}")
                    patched += 1
                graded_list.append(p)
            else:
                graded_list.append(pred)
        print(f"\n  Patched {patched} games with Delta fields.")
        if not args.dry_run:
            data["predictions"] = graded_list
            save_predictions(date, data)
        return

    if not ungraded:
        print("  ✅ Already graded. Run with --regrade to backfill Delta fields.")
        return

    fixtures = fetch_fixtures_for_date(date)
    print(f"  Got {len(fixtures)} finished games from API")

    if not fixtures: return

    # Map (league_id, home, away) -> (home_score, away_score, status, ht_home, ht_away)
    results_map = {}
    for fix in fixtures:
        lid = fix["league"]["id"]
        h_name = fix["teams"]["home"]["name"]
        a_name = fix["teams"]["away"]["name"]
        status = fix.get("status", {}).get("short")
        h_scores = fix.get("scores", {}).get("home", {})
        a_scores = fix.get("scores", {}).get("away", {})
        h_score = h_scores.get("total")
        a_score = a_scores.get("total")
        # Halftime = Q1 + Q2 (may be None if API didn't return quarters)
        h_q1 = h_scores.get("quarter_1") or 0
        h_q2 = h_scores.get("quarter_2") or 0
        a_q1 = a_scores.get("quarter_1") or 0
        a_q2 = a_scores.get("quarter_2") or 0
        ht_home = (h_q1 + h_q2) if (h_scores.get("quarter_1") is not None) else None
        ht_away = (a_q1 + a_q2) if (a_scores.get("quarter_1") is not None) else None
        if h_score is not None and a_score is not None:
            results_map[(lid, h_name, a_name)] = (int(h_score), int(a_score), status, ht_home, ht_away)

    matched = 0
    graded_list = []
    wins_by_model  = {}   # { model_architecture: win_count }
    total_by_model = {}   # { model_architecture: total_count }

    for pred in predictions:
        if pred.get("actual_result"):
            graded_list.append(pred)
            continue
        
        key = (pred["league_id"], pred["home_team"], pred["away_team"])
        # Bug 2: Fuzzy fallback if exact key not found
        if key not in results_map:
            pred_home_n = _normalize_name(pred["home_team"])
            pred_away_n = _normalize_name(pred["away_team"])
            for (lid, h, a), val in results_map.items():
                if lid == pred["league_id"] and _normalize_name(h) == pred_home_n and _normalize_name(a) == pred_away_n:
                    key = (lid, h, a)
                    break
        if key in results_map:
            h_s, a_s, status, ht_home, ht_away = results_map[key]

            # Skip awarded/forfeited matches — 0-20 or 20-0 scores are not real game totals.
            # API short codes for awarded: 'FT:AW', 'AWD', 'WO' (walkover).
            # Also catch the unmistakable 0-20 / 20-0 score pattern as a fallback.
            is_awarded_status = status in ('FT:AW', 'AWD', 'WO', 'AWARDED')
            is_awarded_score  = (h_s == 0 and a_s == 20) or (h_s == 20 and a_s == 0)
            if is_awarded_status or is_awarded_score:
                p = pred.copy()
                p['awarded_match'] = True
                graded_list.append(p)
                print(f"  Skipping awarded match: {pred.get('home_team')} vs {pred.get('away_team')} ({h_s}-{a_s}, status={status})")
                continue

            actual = "HOME" if h_s > a_s else "AWAY"
            
            p = pred.copy()
            p["actual_home_score"] = h_s
            p["actual_away_score"] = a_s
            p["actual_result"]     = actual
            p["status"]            = status

            # Store halftime scores if available from the API
            if ht_home is not None and ht_away is not None:
                ht_total = ht_home + ht_away
                model_total_for_ht = p.get("model_total") or p.get("model", {}).get("total")
                p["halftime_home_score"] = ht_home
                p["halftime_away_score"] = ht_away
                p["halftime_total"]      = ht_total
                if model_total_for_ht:
                    p["halftime_pct_of_model"] = round((ht_total / model_total_for_ht) * 100, 1)
            
            # The Delta Grading Matrix
            # Bug 1 Fix: read flat model_total key (set by run_basketball_daily.py)
            model_total = p.get("model_total") or p.get("model", {}).get("total")
            if model_total:
                if status == "AOT":
                    p["accuracy_tier"] = "OT WARP"
                    p["total_delta"] = None
                    p["total_rpe"] = None
                else:
                    actual_total = h_s + a_s
                    delta = abs(actual_total - model_total)
                    signed_delta = actual_total - model_total
                    rpe = (delta / actual_total) * 100 if actual_total > 0 else 0
                    p["total_delta"] = round(delta, 2)
                    p["signed_delta"] = round(signed_delta, 2)
                    p["total_rpe"] = round(rpe, 2)
                    p["accuracy_tier"] = _delta_tier(delta)
            
            # Outcome grade
            mdl = p.get("model_architecture", "[  SRS   ]")
            is_win = (p.get("predicted_result") == actual)
            wins_by_model[mdl]  = wins_by_model.get(mdl, 0)  + (1 if is_win else 0)
            total_by_model[mdl] = total_by_model.get(mdl, 0) + 1
            
            # Formatted Output
            tier_str = p.get("accuracy_tier", "")
            print(f"  [OK] {pred['home_team']} {h_s}-{a_s} {pred['away_team']} ({mdl.strip()}) -> {actual} ({'WIN' if is_win else 'LOSS'}) | {tier_str}")
            graded_list.append(p)
            matched += 1
        else:
            graded_list.append(pred)

    # Per-model summary line
    for mdl, tot in total_by_model.items():
        w = wins_by_model.get(mdl, 0)
        label = mdl.strip()
        pct_str = f" ({100*w//tot}%)" if tot else ""
        print(f"  [{label}] Matched: {matched} | Accuracy: {w}/{tot}{pct_str}")

    if not args.dry_run:
        data["predictions"] = graded_list
        data["graded_at"] = datetime.now().isoformat()
        # Build per-model grade summary
        grade_summary_by_model = {}
        for mdl, tot in total_by_model.items():
            w = wins_by_model.get(mdl, 0)
            grade_summary_by_model[mdl.strip()] = {
                "wins": w, "total": tot,
                "pct": round(100 * w / tot, 1) if tot else 0
            }
        data["grade_summary"] = grade_summary_by_model
        save_predictions(date, data)

if __name__ == "__main__":
    main()
