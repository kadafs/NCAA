"""
run_basketball_daily.py
========================
Universal daily basketball prediction runner.
Chains: fixtures -> team stats -> league config -> engine -> predictions output.

Works for ANY league available on api-basketball.com.

Usage:
    python run_basketball_daily.py                         # all leagues today
    python run_basketball_daily.py --league_id 40          # BBL Germany only
    python run_basketball_daily.py --date 2026-03-20       # specific date
    python run_basketball_daily.py --min_games 3           # only leagues with 3+ games
    python run_basketball_daily.py --mode full             # full sharp layer
    python run_basketball_daily.py --refresh               # re-fetch fixtures from API
    python run_basketball_daily.py --trace                 # show engine math trace

Output:
    Console: matchup-by-matchup prediction table
    File:    data/basketball_predictions_YYYY-MM-DD.json
"""

import io
import sys
import os
import json
import argparse
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from glob import glob
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass  # Python < 3.7

# Add project root
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ET_TZ    = timezone.utc


# ------------------------------------------------------------------
# LEAGUES EXCLUDED FROM THIS RUNNER
# These are covered by dedicated scripts with individually tuned models:
#   NBA   -> run_universal.py --league nba
#   NCAA  -> run_universal.py --league ncaa
#   NBL   -> run_universal.py --league nbl
#   NBL1  -> run_universal.py --league nbl1  (5 conference IDs)
# ------------------------------------------------------------------
EXCLUDED_LEAGUE_IDS = {
    12,    # NBA
    116,   # NCAA (api-basketball ID)
    8,     # NBL Australia
    207,   # NBL1 North
    209,   # NBL1 South
    212,   # NBL1 Central
    214,   # NBL1 West
    215,   # NBL1 East
}

EXCLUDED_LEAGUE_NAMES = {
    "NBA", "NCAA", "NBL",
    "NBL1 North", "NBL1 South", "NBL1 Central", "NBL1 West", "NBL1 East",
}


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def get_today_str(date_str=None):
    if date_str:
        return date_str
    return datetime.now(ET_TZ).strftime("%Y-%m-%d")


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ------------------------------------------------------------------
# STEP 1: FETCH TODAY'S FIXTURES
# ------------------------------------------------------------------

def fetch_today_fixtures(date_str, refresh=False):
    """
    Returns all games for today from api-basketball.com.
    Uses cached file if available and refresh=False.
    """
    cache_path = f"data/api_basketball_today_{date_str}.json"

    if not refresh and os.path.exists(cache_path):
        print(f"  Using cached fixtures: {cache_path}")
        data = load_json(cache_path)
        return data.get("leagues_summary", [])

    print(f"  Fetching fixtures for {date_str} from api-basketball.com...")
    try:
        r = requests.get(
            f"{BASE_URL}/games",
            headers=HEADERS,
            params={"date": date_str},
            timeout=15,
        )
        all_games = r.json().get("response", [])
        total = r.json().get("results", 0)
        print(f"  Got {total} games.")
    except Exception as e:
        print(f"  ERROR fetching fixtures: {e}")
        return []

    from collections import defaultdict
    by_league = defaultdict(list)
    for game in all_games:
        league = game.get("league", {})
        lid    = league.get("id")
        lname  = league.get("name", "Unknown")
        country = game.get("country", {}).get("name", "")
        season = game.get("season")
        home = game.get("teams", {}).get("home", {}).get("name", "?")
        away = game.get("teams", {}).get("away", {}).get("name", "?")
        hs = game.get("scores", {}).get("home", {}).get("total")
        as_ = game.get("scores", {}).get("away", {}).get("total")
        by_league[(lid, lname, country, season)].append({
            "home": home, "away": away,
            "home_score": hs, "away_score": as_,
            "time": game.get("date", "")[:16].replace("T", " "),
            "status": game.get("status", {}).get("long", "Scheduled"),
        })

    leagues_summary = [
        {
            "league_id": lid, "league_name": lname,
            "country": country, "season": season,
            "game_count": len(games), "games": games,
        }
        for (lid, lname, country, season), games in
        sorted(by_league.items(), key=lambda x: x[0][1])
    ]

    out = {"date": date_str, "total_games": total, "leagues_summary": leagues_summary}
    save_json(cache_path, out)
    return leagues_summary


# ------------------------------------------------------------------
# STEP 2: LOAD OR CALIBRATE CONFIG
# ------------------------------------------------------------------

def get_or_calibrate_config(league_id, league_name, auto_calibrate=True):
    """
    Load config for league_id. Auto-calibrate if missing.
    Returns (config_path, config_dict) or (None, None) if unavailable.
    """
    config_path = f"configs/leagues/{league_id}.json"

    if os.path.exists(config_path):
        cfg = load_json(config_path)
        return config_path, cfg

    if auto_calibrate:
        print(f"    No config found — auto-calibrating league {league_id}...")
        try:
            from calibrate_league import calibrate_one
            cfg = calibrate_one(league_id=league_id, verbose=False)
            return config_path, cfg
        except Exception as e:
            print(f"    Calibration failed: {e}")

    return None, None


# ------------------------------------------------------------------
# STEP 3: LOAD OR FETCH TEAM STATS
# ------------------------------------------------------------------

def get_or_fetch_stats(league_id, season, refresh=False):
    """
    Load cached team stats or fetch fresh from API.
    Returns {team_name: {adj_off, adj_def, adj_t, ...}} or {}.
    """
    from fetch_universal_bball_stats import get_current_season, fetch_stats

    # Auto-detect season if not provided by fixture file
    if not season:
        season = get_current_season(league_id)

    # Check for exact cache file
    exact_path = f"data/bball_stats_{league_id}_{season}.json"
    if not refresh and os.path.exists(exact_path):
        data = load_json(exact_path)
        return data.get("teams", {})

    # Broader cache search: any season file for this league
    if not refresh:
        existing = sorted(glob(f"data/bball_stats_{league_id}_*.json"), reverse=True)
        if existing:
            data = load_json(existing[0])
            teams = data.get("teams", {})
            if teams:
                return teams

    # Fetch fresh
    try:
        return fetch_stats(league_id, season=season, verbose=False)
    except Exception as e:
        print(f"    Stats fetch failed: {e}")
        return {}


# ------------------------------------------------------------------
# STEP 4: FUZZY TEAM MATCHING
# ------------------------------------------------------------------

def find_team(name, stats_dict):
    """
    Case-insensitive + partial fuzzy match of team name against stats dict keys.
    Returns (matched_key, stats) or (None, None).
    """
    if not name or not stats_dict:
        return None, None

    name_lower = name.lower().strip()

    # Exact match
    if name in stats_dict:
        return name, stats_dict[name]

    # Case-insensitive
    for k in stats_dict:
        if k.lower() == name_lower:
            return k, stats_dict[k]

    # Partial: name contains key or key contains name
    for k in stats_dict:
        k_lower = k.lower()
        if k_lower in name_lower or name_lower in k_lower:
            return k, stats_dict[k]

    # Word overlap
    name_words = set(name_lower.split())
    best_key, best_score = None, 0
    for k in stats_dict:
        k_words = set(k.lower().split())
        overlap = len(name_words & k_words)
        if overlap > best_score:
            best_key, best_score = k, overlap
    if best_score >= 1:
        return best_key, stats_dict[best_key]

    return None, None


# ------------------------------------------------------------------
# STEP 5: PREDICT ONE GAME
# ------------------------------------------------------------------

def predict_game(away_name, home_name, team_stats, config, config_path, mode, trace):
    """
    Run the UniversalBasketballEngine for a single matchup.
    Returns engine result dict or None if teams not found.
    """
    from core.basketball_engine import UniversalBasketballEngine

    away_key, sA = find_team(away_name, team_stats)
    home_key, sH = find_team(home_name, team_stats)

    if not sA or not sH:
        missing = []
        if not sA: missing.append(away_name)
        if not sH: missing.append(home_name)
        return None, f"Team stats not found: {', '.join(missing)}"

    # Build game_data in the format the engine expects
    cfg = config
    game_data = {
        "team":       away_name,
        "opponent":   home_name,
        "statsA":     sA,
        "statsH":     sH,
        # Pace: average of both teams (adj_t)
        "pace_adjustment":      (sA.get("adj_t", cfg.get("pace_pivot", 76)) +
                                 sH.get("adj_t", cfg.get("pace_pivot", 76))) / 2,
        "efficiency_adjustment": (sA.get("adj_off", cfg.get("eff_pivot", 108)) +
                                  sH.get("adj_off", cfg.get("eff_pivot", 108))) / 2,
        # Spread estimate (simple, for sharp layer gates)
        "projected_spread": abs(
            sH.get("adj_off", 108) - sA.get("adj_off", 108)
        ) / 2,
        "market_total": None,  # No market line for most leagues
        "is_neutral": False,
    }

    try:
        engine = UniversalBasketballEngine(config_path, mode=mode)
        engine.trace_enabled = trace
        result = engine.calculate_total(game_data, injury_notes=[])
        return result, None
    except Exception as e:
        return None, str(e)


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Universal Daily Basketball Predictions")
    parser.add_argument("--date",       help="Date YYYY-MM-DD (default: today)")
    parser.add_argument("--league_id",  type=int, help="Only run one league")
    parser.add_argument("--mode",       choices=["safe", "full"], default="safe")
    parser.add_argument("--min_games",  type=int, default=1,
                        help="Skip leagues with fewer than this many games today")
    parser.add_argument("--refresh",    action="store_true", help="Re-fetch fixtures from API")
    parser.add_argument("--trace",      action="store_true", help="Show engine math trace")
    parser.add_argument("--no_calibrate", action="store_true",
                        help="Skip auto-calibration (use existing configs only)")
    args = parser.parse_args()

    date_str = get_today_str(args.date)

    print("\n" + "=" * 70)
    print(f"  UNIVERSAL BASKETBALL PREDICTIONS | {date_str} | {args.mode.upper()}")
    print("=" * 70)

    # Step 1: get fixtures
    leagues = fetch_today_fixtures(date_str, refresh=args.refresh)
    if not leagues:
        print("  No fixtures found. Check API key or try --refresh.")
        return

    # Filter — always exclude dedicated-model leagues
    leagues = [
        l for l in leagues
        if l["league_id"] not in EXCLUDED_LEAGUE_IDS
        and l["league_name"] not in EXCLUDED_LEAGUE_NAMES
    ]
    if args.league_id:
        leagues = [l for l in leagues if l["league_id"] == args.league_id]
    if args.min_games > 1:
        leagues = [l for l in leagues if l["game_count"] >= args.min_games]

    print(f"  Running predictions for {len(leagues)} league(s)...\n")

    all_predictions = []
    total_predicted = 0
    total_skipped   = 0

    for league_entry in leagues:
        lid      = league_entry["league_id"]
        lname    = league_entry["league_name"]
        country  = league_entry.get("country", "")
        season   = league_entry.get("season")
        games    = league_entry["games"]

        # Skip already-finished games if they have scores
        upcoming = [g for g in games if g.get("status") not in
                    ("Game Finished", "Final", "AOT")]
        if not upcoming:
            upcoming = games  # Show all if all finished (useful for backtesting)

        print(f"  [{lid}] {lname} ({country}) — {len(games)} game(s)")

        # Step 2: config
        config_path, config = get_or_calibrate_config(
            lid, lname, auto_calibrate=not args.no_calibrate
        )
        if not config_path:
            print(f"    SKIP -- no config available\n")
            total_skipped += len(games)
            continue

        # Step 3: team stats
        stats = get_or_fetch_stats(lid, season, refresh=args.refresh)
        if not stats:
            print(f"    SKIP — no team stats available\n")
            total_skipped += len(games)
            continue

        # Step 4: predict each game
        for game in games:
            away = game["away"]
            home = game["home"]
            status = game.get("status", "")

            result, err = predict_game(
                away, home, stats, config, config_path, args.mode, args.trace
            )

            if err:
                print(f"    {away} @ {home}  -- SKIP ({err})")
                total_skipped += 1
                continue

            model_total = result["final_model_total"]
            market      = result["market_total"]
            edge        = result["edge"]
            decision    = result["decision"]
            confidence  = result["confidence"]
            side        = result["side"]

            # Format output line
            if market and market != 145.5 and market != 230.0:
                # Real market line was provided
                mkt_str = f"Mkt:{market:.1f}"
                edge_str = f"Edge:{edge:+.1f} {side} [{confidence}] -> {decision}"
            else:
                mkt_str = "Mkt:N/A"
                edge_str = "MODEL ONLY (no market line)"

            score_str = ""
            if game.get("home_score") is not None:
                score_str = f"  Final: {game['away_score']}-{game['home_score']}"

            print(f"    {away:28} @ {home:28}")
            print(f"      Model:{model_total:.1f}  {mkt_str}  {edge_str}{score_str}")

            if args.trace:
                for t in result.get("trace", []):
                    print(f"        > {t}")

            # Build record
            all_predictions.append({
                "league_id":    lid,
                "league":       lname,
                "country":      country,
                "date":         date_str,
                "away_team":    away,
                "home_team":    home,
                "status":       status,
                "model_total":  model_total,
                "market_total": market if (market and market not in (145.5, 230.0)) else None,
                "edge":         edge if (market and market not in (145.5, 230.0)) else None,
                "side":         side if (market and market not in (145.5, 230.0)) else None,
                "decision":     decision if (market and market not in (145.5, 230.0)) else "MODEL ONLY",
                "confidence":   confidence,
                "mode":         args.mode,
                "config_source": config.get("_source", "unknown"),
                "tier":         config.get("_tier", "unknown"),
                "timestamp":    datetime.now(ET_TZ).isoformat(),
            })
            total_predicted += 1

        print()

    # Summary
    print("=" * 70)
    print(f"  COMPLETE: {total_predicted} predictions  |  {total_skipped} skipped")
    print("=" * 70)

    # Save
    if all_predictions:
        out_path = f"data/basketball_predictions_{date_str}.json"
        save_json(out_path, {
            "date": date_str,
            "mode": args.mode,
            "total_predictions": total_predicted,
            "predictions": all_predictions,
        })
        print(f"\n  Saved -> {out_path}")

    print()


if __name__ == "__main__":
    main()
