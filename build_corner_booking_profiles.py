"""
build_corner_booking_profiles.py
──────────────────────────────────
Builds per-team historical corner & booking point profiles by fetching
the last N completed fixtures per team from /fixtures/statistics.

Run manually or via cron (weekly recommended):
    python build_corner_booking_profiles.py
    python build_corner_booking_profiles.py --league 39 --season 2026
    python build_corner_booking_profiles.py --last 10   # use last 10 fixtures per team

Output: data/football/team_profiles_{league_id}.json
"""

import os
import sys
import json
import time
import argparse
import glob
import requests
from datetime import datetime
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

YELLOW_CARD_PTS = 10
RED_CARD_PTS    = 25


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
            return r.json()
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"  ⚠️  {endpoint} failed: {e}")
    return {}


def build_profile_for_team(team_id: int, league_id: int, season: int, last: int) -> dict | None:
    """Fetch last N completed fixtures for a team and compute averages."""
    data = safe_get("/fixtures", {
        "team": team_id, "league": league_id, "season": season,
        "status": "FT", "last": last
    })
    fixtures = data.get("response", [])
    if not fixtures:
        return None

    corners_for_list    = []
    corners_ag_list     = []
    yellow_list         = []
    red_list            = []
    fouls_list          = []
    booking_pts_list    = []
    shots_total_list    = []

    for fix in fixtures:
        fid = fix["fixture"]["id"]
        # Determine which side this team is (home or away)
        is_home = fix["teams"]["home"]["id"] == team_id
        side    = "home" if is_home else "away"
        opp_side = "away" if is_home else "home"

        stat_data = safe_get("/fixtures/statistics", {"fixture": fid})
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
            yellow_list.append(yellow)
            red_list.append(red)
            fouls_list.append(fouls)
            booking_pts_list.append(booking_pts)
            shots_total_list.append(shots)

    n = len(corners_for_list)
    if n == 0:
        return None

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    return {
        "team_id":              team_id,
        "avg_corners_for":      avg(corners_for_list),
        "avg_corners_against":  avg(corners_ag_list),
        "avg_total_corners":    avg([f + a for f, a in zip(corners_for_list, corners_ag_list)]),
        "avg_yellow_cards":     avg(yellow_list),
        "avg_red_cards":        avg(red_list),
        "avg_fouls":            avg(fouls_list),
        "avg_booking_pts":      avg(booking_pts_list),
        "avg_shots_total":      avg(shots_total_list),
        "sample_size":          n,
        "built_at":             datetime.utcnow().isoformat(),
    }


def corners_prediction(home_profile: dict, away_profile: dict) -> dict:
    """
    Predict corner totals and booking points for a match
    given the two team profiles.
    """
    if not home_profile or not away_profile:
        return {}

    # Expected corners: blend team for/against averages
    exp_home_corners = round((home_profile["avg_corners_for"] + away_profile["avg_corners_against"]) / 2, 1)
    exp_away_corners = round((away_profile["avg_corners_for"] + home_profile["avg_corners_against"]) / 2, 1)
    exp_total        = round(exp_home_corners + exp_away_corners, 1)

    # Simple probability model: use Poisson-style threshold comparison
    # P(over N) ≈ 1 - CDF(N, lambda=exp_total)
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

    # Recommended corner line
    if over_10_5 >= 55:
        corner_rec = "OVER 10.5"
    elif over_9_5 >= 60:
        corner_rec = "OVER 9.5"
    elif over_9_5 < 35:
        corner_rec = "UNDER 9.5"
    else:
        corner_rec = "PASS"

    # Expected booking points
    exp_home_booking = round((home_profile["avg_booking_pts"] + away_profile.get("avg_booking_pts", 20)) / 2, 1)
    exp_away_booking = exp_home_booking   # symmetric for now
    exp_total_booking = round(home_profile["avg_booking_pts"] + away_profile["avg_booking_pts"], 1)
    exp_total_yellows = round(home_profile["avg_yellow_cards"] + away_profile["avg_yellow_cards"], 1)

    # Booking points over lines
    over_30_bk = round((1 - poisson_cdf(exp_total_booking / 10, 2)) * 100)  # rough approximation
    over_40_bk = round((1 - poisson_cdf(exp_total_booking / 10, 3)) * 100)

    # Booking recommendation
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
        "corner_recommendation": corner_rec,
        "exp_total_booking_pts":  exp_total_booking,
        "exp_total_yellows":      exp_total_yellows,
        "over_30_booking_pct":    over_30_bk,
        "over_40_booking_pct":    over_40_bk,
        "booking_recommendation": booking_rec,
    }


def build_profiles_for_league(league_id: int, season: int, last: int) -> dict:
    """Fetch all playing teams in a league and build their profiles."""
    # Get team list from recent stats files or fixtures
    teams_data = safe_get("/teams", {"league": league_id, "season": season})
    teams = teams_data.get("response", [])
    if not teams:
        print(f"  No teams found for league {league_id}")
        return {}

    profiles = {}
    print(f"  Building profiles for {len(teams)} teams in league {league_id}...")

    for t in teams:
        team = t.get("team", {})
        tid  = team.get("id")
        name = team.get("name", "Unknown")
        if not tid:
            continue

        print(f"    {name} (id={tid})...", end=" ", flush=True)
        profile = build_profile_for_team(tid, league_id, season, last)
        if profile:
            profile["name"] = name
            profiles[str(tid)] = profile
            print(f"✓ ({profile['sample_size']} fixtures)")
        else:
            print("no data")
        time.sleep(0.3)

    return profiles


def main():
    parser = argparse.ArgumentParser(description="Build corner & booking profiles for football teams.")
    parser.add_argument("--league",  type=int, help="Specific league ID to build (default: all active leagues)")
    parser.add_argument("--season",  type=int, default=2026)
    parser.add_argument("--last",    type=int, default=12, help="Last N completed fixtures per team (default: 12)")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    if args.league:
        league_ids = [args.league]
    else:
        # Auto-discover leagues from existing stats files
        stat_files = glob.glob(os.path.join(DATA_DIR, "universal_*_stats.json"))
        league_ids = sorted(set(
            int(os.path.basename(f).split("_")[1])
            for f in stat_files
            if os.path.basename(f).split("_")[1].isdigit()
        ))
        print(f"Auto-discovered {len(league_ids)} leagues from existing stats files.")

    if not league_ids:
        print("No leagues to process. Use --league <id> or ensure stats files exist.")
        return

    for lid in league_ids:
        print(f"\n{'='*60}")
        print(f"  League {lid}")
        print(f"{'='*60}")

        profiles = build_profiles_for_league(lid, args.season, args.last)
        if not profiles:
            continue

        out_path = os.path.join(DATA_DIR, f"team_profiles_{lid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "league_id": lid,
                "season":    args.season,
                "built_at":  datetime.utcnow().isoformat(),
                "teams":     profiles
            }, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Saved {len(profiles)} team profiles → {out_path}")

    print("\n✅ All profiles built!")


if __name__ == "__main__":
    main()
