"""
fetch_universal_bball_stats.py
================================
Fetches team stats for any api-basketball.com league and derives the
adj_off, adj_def, adj_t values the UniversalBasketballEngine needs.

Uses the /standings endpoint (1 API call per league) for efficiency.
Falls back to /games season aggregate if standings are unavailable.

Usage:
    python fetch_universal_bball_stats.py --league_id 40 --season 2025
    python fetch_universal_bball_stats.py --league_id 40  # auto-detect season
    python fetch_universal_bball_stats.py --all           # all leagues from today's fixture file

Output:
    data/bball_stats_<league_id>_<season>.json
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
        pass

load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ET_TZ = ZoneInfo("America/New_York")


def get_current_season(league_id):
    """Auto-detect the current season for a league. Always returns an integer start year."""
    try:
        r = requests.get(f"{BASE_URL}/leagues", headers=HEADERS,
                         params={"id": league_id}, timeout=10)
        leagues = r.json().get("response", [])
        if leagues:
            seasons = leagues[0].get("seasons", [])
            if seasons:
                raw = sorted(seasons, key=lambda s: str(s.get("season", 0)))[-1].get("season")
                # Handle both int (2025) and string ('2025-2026') season formats
                if isinstance(raw, str) and "-" in raw:
                    return int(raw.split("-")[0])
                return int(raw)
    except Exception:
        pass
    now = datetime.now(ET_TZ)
    return now.year if now.month >= 9 else now.year - 1


def load_config(league_id):
    """Load the league config to get pace_pivot and eff_pivot for stat derivation."""
    # Try numeric ID config first (auto-calibrated), then named configs
    for path in [f"configs/leagues/{league_id}.json"]:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    # Default fallback pivots
    return {"pace_pivot": 76.0, "eff_pivot": 108.0}


def derive_team_stats(team_data, pace_pivot, eff_pivot):
    """
    Convert raw standings/PPG data into engine-compatible stats dict.

    adj_t   = pace proxy (possessions per 40 min) — approximated from league pace_pivot
    adj_off = points per 100 possessions (offensive efficiency)
    adj_def = opponent points per 100 possessions (defensive efficiency)
    """
    ppg     = team_data.get("ppg", 0)       # Points scored per game
    opp_ppg = team_data.get("opp_ppg", 0)   # Points allowed per game

    # Derive adj_off and adj_def from raw PPG
    # Formula: efficiency = PPG / (pace_pivot / 100)
    adj_off = (ppg     / (pace_pivot / 100)) if pace_pivot > 0 else eff_pivot
    adj_def = (opp_ppg / (pace_pivot / 100)) if pace_pivot > 0 else eff_pivot

    # Clamp to sensible ranges
    adj_off = max(70.0, min(135.0, adj_off))
    adj_def = max(70.0, min(135.0, adj_def))

    return {
        "adj_t":   round(pace_pivot, 1),   # Use league pace as team pace (refined later)
        "adj_off": round(adj_off, 1),
        "adj_def": round(adj_def, 1),
        "ppg":     round(ppg, 1),
        "opp_ppg": round(opp_ppg, 1),
        "games":   team_data.get("games", 0),
        "wins":    team_data.get("wins", 0),
        "losses":  team_data.get("losses", 0),
    }


def fetch_via_standings(league_id, season, pace_pivot, eff_pivot):
    """
    Fetch team stats from /standings endpoint.
    Returns {team_name: stats_dict} or {} on failure.
    """
    try:
        r = requests.get(
            f"{BASE_URL}/standings",
            headers=HEADERS,
            params={"league": league_id, "season": season},
            timeout=12,
        )
        data = r.json().get("response", [])
        if not data:
            return {}

        team_stats = {}

        # standings response is a list of groups (conferences/divisions)
        for group in data:
            if isinstance(group, list):
                entries = group
            elif isinstance(group, dict):
                entries = [group]
            else:
                continue

            for entry in entries:
                team_obj  = entry.get("team", {})
                team_name = team_obj.get("name", "Unknown")
                games_obj = entry.get("games", {})
                played    = games_obj.get("played", {})
                wins_obj  = entry.get("wins", {})
                losses_obj = entry.get("losses", {})
                pts_obj   = entry.get("points", {})

                games_played = played.get("total", 0) if isinstance(played, dict) else played
                wins  = wins_obj.get("total", 0) if isinstance(wins_obj, dict) else wins_obj
                losses = losses_obj.get("total", 0) if isinstance(losses_obj, dict) else losses_obj
                pts_for  = pts_obj.get("for", {})
                pts_agn  = pts_obj.get("against", {})

                if isinstance(pts_for, dict):
                    ppg = pts_for.get("average", {})
                    ppg = ppg.get("total", 0) if isinstance(ppg, dict) else ppg
                else:
                    ppg = 0

                if isinstance(pts_agn, dict):
                    opp_ppg = pts_agn.get("average", {})
                    opp_ppg = opp_ppg.get("total", 0) if isinstance(opp_ppg, dict) else opp_ppg
                else:
                    opp_ppg = 0

                ppg     = float(ppg) if ppg else 0.0
                opp_ppg = float(opp_ppg) if opp_ppg else 0.0

                if team_name and ppg > 0:
                    team_stats[team_name] = derive_team_stats(
                        {"ppg": ppg, "opp_ppg": opp_ppg,
                         "games": games_played, "wins": wins, "losses": losses},
                        pace_pivot, eff_pivot
                    )

        return team_stats

    except Exception as e:
        print(f"  [Standings Error] league={league_id} season={season}: {e}")
        return {}


def fetch_via_games_aggregate(league_id, season, pace_pivot, eff_pivot):
    """
    Fallback: derive team stats by aggregating all season game results.
    More API calls but works when /standings is not populated.
    """
    try:
        r = requests.get(
            f"{BASE_URL}/games",
            headers=HEADERS,
            params={"league": league_id, "season": season},
            timeout=15,
        )
        all_games = r.json().get("response", [])

        from collections import defaultdict
        scoring  = defaultdict(list)  # team -> list of points scored
        conceded = defaultdict(list)  # team -> list of points allowed

        for g in all_games:
            status = g.get("status", {}).get("short", "")
            if status not in ("FT", "AOT"):
                continue
            home_name  = g.get("teams", {}).get("home", {}).get("name", "")
            away_name  = g.get("teams", {}).get("away", {}).get("name", "")
            home_score = g.get("scores", {}).get("home", {}).get("total")
            away_score = g.get("scores", {}).get("away", {}).get("total")
            if not home_score or not away_score:
                continue
            home_score = int(home_score)
            away_score = int(away_score)
            if home_name:
                scoring[home_name].append(home_score)
                conceded[home_name].append(away_score)
            if away_name:
                scoring[away_name].append(away_score)
                conceded[away_name].append(home_score)

        team_stats = {}
        for team in scoring:
            pts    = scoring[team]
            opp    = conceded[team]
            n      = len(pts)
            ppg    = sum(pts) / n if n else 0
            opp_ppg = sum(opp) / n if n else 0
            team_stats[team] = derive_team_stats(
                {"ppg": ppg, "opp_ppg": opp_ppg, "games": n},
                pace_pivot, eff_pivot
            )

        return team_stats

    except Exception as e:
        print(f"  [Games Aggregate Error] league={league_id} season={season}: {e}")
        return {}


def fetch_via_daily_cache(league_id, pace_pivot, eff_pivot):
    """
    Build rolling team stats by aggregating all cached daily game files.
    These are the data/api_basketball_today_YYYY-MM-DD.json files we accumulate.
    This works on the FREE tier since those files are built from /games?date= calls.
    Returns {team_name: stats_dict} or {}.
    """
    from collections import defaultdict

    cache_files = sorted(glob("data/api_basketball_today_*.json"))
    if not cache_files:
        return {}

    scoring  = defaultdict(list)
    conceded = defaultdict(list)
    games_found = 0

    for cache_file in cache_files:
        try:
            with open(cache_file, encoding="utf-8") as f:
                day_data = json.load(f)
        except Exception:
            continue

        for league_entry in day_data.get("leagues_summary", []):
            if league_entry.get("league_id") != league_id:
                continue
            for g in league_entry.get("games", []):
                # Extract scores — handle both integer fields and 'score' string format
                hs, as_ = None, None

                # Format A: home_score / away_score integer fields (from run_basketball_daily.py)
                if g.get("home_score") is not None and g.get("away_score") is not None:
                    try:
                        hs  = int(g["home_score"])
                        as_ = int(g["away_score"])
                    except (TypeError, ValueError):
                        pass

                # Format B: 'score' string like '68-81' (from explore_api_basketball_today.py)
                elif g.get("score") and "-" in str(g["score"]):
                    parts = str(g["score"]).split("-")
                    if len(parts) == 2:
                        try:
                            # In '68-81', first number is home, second is away
                            hs  = int(parts[0].strip())
                            as_ = int(parts[1].strip())
                        except ValueError:
                            pass

                if hs is None or as_ is None or (hs == 0 and as_ == 0):
                    continue

                home = g.get("home", "")
                away = g.get("away", "")
                if home:
                    scoring[home].append(hs)
                    conceded[home].append(as_)
                if away:
                    scoring[away].append(as_)
                    conceded[away].append(hs)
                games_found += 1

    if not scoring:
        return {}

    team_stats = {}
    for team in scoring:
        pts     = scoring[team]
        opp     = conceded[team]
        n       = len(pts)
        ppg     = sum(pts) / n
        opp_ppg = sum(opp) / n
        team_stats[team] = derive_team_stats(
            {"ppg": ppg, "opp_ppg": opp_ppg, "games": n},
            pace_pivot, eff_pivot
        )

    return team_stats, games_found


def fetch_stats(league_id, season=None, verbose=True):
    """
    Main entry point. Priority order:
      1. Daily cache aggregate (free tier — always works)
      2. /standings API call (paid tier)
      3. /games season aggregate (paid tier)
    Returns team_stats dict and saves to data/bball_stats_<id>_<season>.json.
    """
    if season is None:
        season = get_current_season(league_id)

    if verbose:
        print(f"\n  Fetching stats: league={league_id}  season={season}")

    cfg = load_config(league_id)
    pace_pivot = cfg.get("pace_pivot", 76.0)
    eff_pivot  = cfg.get("eff_pivot", 108.0)

    # Strategy 1: Build from daily cache files (always works on free tier)
    result = fetch_via_daily_cache(league_id, pace_pivot, eff_pivot)
    if isinstance(result, tuple):
        team_stats, games_found = result
    else:
        team_stats, games_found = result, 0

    if team_stats:
        if verbose:
            print(f"  Built from {games_found} cached game results across {len(glob('data/api_basketball_today_*.json'))} daily files")
    else:
        # Strategy 2: Try standings API (paid tier)
        team_stats = fetch_via_standings(league_id, season, pace_pivot, eff_pivot)
        if team_stats:
            if verbose:
                print("  Built from /standings API")
        else:
            # Strategy 3: Season game aggregate (paid tier)
            if verbose:
                print("  Standings empty — trying game aggregate...")
            team_stats = fetch_via_games_aggregate(league_id, season, pace_pivot, eff_pivot)
            if team_stats and verbose:
                print("  Built from /games season aggregate")

    if verbose:
        print(f"  Teams found: {len(team_stats)}")
        if team_stats:
            sample = list(team_stats.items())[:3]
            for name, s in sample:
                print(f"    {name:30} adj_off={s['adj_off']:.1f}  adj_def={s['adj_def']:.1f}  "
                      f"adj_t={s['adj_t']:.1f}  ({s['games']} games)")

    if not team_stats:
        if verbose:
            print("  WARNING: No team stats found. Run more daily fixture fetches to accumulate data.")
        return {}

    # Save
    os.makedirs("data", exist_ok=True)
    out_path = f"data/bball_stats_{league_id}_{season}.json"
    output = {
        "league_id": league_id,
        "season": season,
        "pace_pivot": pace_pivot,
        "eff_pivot": eff_pivot,
        "fetched_at": datetime.now(ET_TZ).isoformat(),
        "team_count": len(team_stats),
        "teams": team_stats,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    if verbose:
        print(f"  Saved -> {out_path}")

    return team_stats


def fetch_all_from_today(verbose=True):
    """Fetch stats for all leagues in today's fixture file."""
    files = sorted(glob("data/api_basketball_today_*.json"), reverse=True)
    if not files:
        print("No today's fixture file found. Run explore_api_basketball_today.py first.")
        return

    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)

    leagues = data.get("leagues_summary", [])
    print(f"\nFetching stats for {len(leagues)} leagues from {files[0]}...")
    print("=" * 60)

    results = []
    for entry in leagues:
        lid  = entry["league_id"]
        name = entry["league_name"]
        print(f"\n[{lid}] {name}")
        try:
            stats = fetch_stats(lid, verbose=verbose)
            results.append({"league_id": lid, "name": name,
                            "teams": len(stats), "status": "ok"})
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"league_id": lid, "name": name, "status": "error", "error": str(e)})

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\nDone. {ok}/{len(results)} leagues fetched.")
    return results


def main():
    parser = argparse.ArgumentParser(description="Fetch team stats for any basketball league")
    parser.add_argument("--league_id", type=int, help="League ID")
    parser.add_argument("--season",    type=int, help="Season year (default: auto-detect)")
    parser.add_argument("--all",       action="store_true", help="Fetch all leagues from today's fixture file")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: API_BASKETBALL_KEY not set in .env")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  UNIVERSAL BASKETBALL STATS FETCHER")
    print("=" * 60)

    if args.all:
        fetch_all_from_today()
    elif args.league_id:
        fetch_stats(args.league_id, season=args.season)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
