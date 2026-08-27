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
        return {"quarantined": True, "reason": "No corner/booking stats in FT fixtures"}

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
            continue

        profile = build_profile_for_team(tid, league_id, season, last)
        if profile:
            if profile.get("quarantined"):
                print("quarantined (no stats)")
                profiles[str(tid)] = profile
            else:
                profile["name"] = name
                profiles[str(tid)] = profile
                print(f"✓ ({profile['sample_size']} fixtures)")
        else:
            print("no data (no FT fixtures)")
        time.sleep(0.3)

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
        max_age_hours = 23.0
    else:
        max_age_hours = 160.0

    if args.league:
        league_ids = [args.league]

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
