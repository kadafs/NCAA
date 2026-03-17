"""
fetch_basketball_fixtures.py
============================
Standalone daily fixture fetcher for ALL basketball leagues.
Queries each league's data source independently -- no prediction engine required.

Usage:
    python fetch_basketball_fixtures.py
    python fetch_basketball_fixtures.py --date 2026-03-15
    python fetch_basketball_fixtures.py --league nba
    python fetch_basketball_fixtures.py --league nbl1 --date 2026-03-29

Supported leagues:
    nba, ncaa, nbl, nbl1, euro, eurocup, acb

Output:
    Prints a clean fixture table to console + saves to data/basketball_fixtures_YYYY-MM-DD.json
"""

import os
import sys
import io
import json
import argparse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

load_dotenv()

API_BASKETBALL_KEY = os.getenv("API_BASKETBALL_KEY")
API_BASKETBALL_BASE = "https://v1.basketball.api-sports.io"
API_BASKETBALL_HEADERS = {"x-apisports-key": API_BASKETBALL_KEY}

ET_TZ = ZoneInfo("America/New_York")
AU_TZ = ZoneInfo("Australia/Sydney")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_target_date(date_str=None):
    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    return datetime.now(ET_TZ).date()


def print_league_header(name, count, date_str):
    bar = "-" * 60
    print(f"\n{bar}")
    print(f"  [BBALL] {name.upper()} | {date_str}  ({count} game{'s' if count != 1 else ''})")
    print(bar)


def print_game(away, home, start_time=None, status=None, league_note=None):
    time_part = f"  {start_time}" if start_time else ""
    status_part = f"  [{status}]" if status else ""
    note_part = f"  ({league_note})" if league_note else ""
    print(f"  {away}  @  {home}{time_part}{status_part}{note_part}")


def api_basketball_games_by_date(league_id, season, date_str):
    """Generic api-basketball.com /games call filtered by date."""
    try:
        r = requests.get(
            f"{API_BASKETBALL_BASE}/games",
            headers=API_BASKETBALL_HEADERS,
            params={"league": league_id, "season": season, "date": date_str},
            timeout=10,
        )
        return r.json().get("response", [])
    except Exception as e:
        print(f"  [api-basketball] Error for league {league_id}: {e}")
        return []


def parse_api_basketball_game(game, conference=None):
    """Parse a raw api-basketball.com game object into a clean dict."""
    teams = game.get("teams", {})
    scores = game.get("scores", {})
    status = game.get("status", {})
    home = teams.get("home", {})
    away = teams.get("away", {})
    return {
        "game_id":   game.get("id"),
        "home_team": home.get("name"),
        "away_team": away.get("name"),
        "start_time": game.get("date", "")[:16].replace("T", " "),
        "status":    status.get("long", "Scheduled"),
        "home_score": scores.get("home", {}).get("total"),
        "away_score": scores.get("away", {}).get("total"),
        "conference": conference,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NBA
# ─────────────────────────────────────────────────────────────────────────────

def fetch_nba(target_date):
    """
    Queries ESPN's public NBA scoreboard API.
    No API key required. Falls back gracefully.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    espn_date = target_date.strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={espn_date}"
    games = []
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        for event in data.get("events", []):
            comp = event["competitions"][0]
            home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
            away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
            status = event.get("status", {}).get("type", {}).get("description", "Scheduled")
            games.append({
                "game_id":   event.get("id"),
                "home_team": f"{home['team']['location']} {home['team']['name']}",
                "away_team": f"{away['team']['location']} {away['team']['name']}",
                "start_time": event.get("date", "")[:16].replace("T", " "),
                "status":    status,
                "home_score": home.get("score"),
                "away_score": away.get("score"),
                "conference": None,
            })
    except Exception as e:
        print(f"  [NBA/ESPN] Error: {e}")
    return games


# ─────────────────────────────────────────────────────────────────────────────
# NCAA
# ─────────────────────────────────────────────────────────────────────────────

def fetch_ncaa(target_date):
    """
    Queries ESPN's public NCAA Men's Basketball scoreboard API.
    No API key required.
    """
    espn_date = target_date.strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={espn_date}"
    games = []
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        for event in data.get("events", []):
            comp = event["competitions"][0]
            home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
            away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
            status = event.get("status", {}).get("type", {}).get("description", "Scheduled")
            conf_note = comp.get("conferenceCompetition", False)
            games.append({
                "game_id":   event.get("id"),
                "home_team": home["team"].get("displayName", home["team"].get("name", "Unknown")),
                "away_team": away["team"].get("displayName", away["team"].get("name", "Unknown")),
                "start_time": event.get("date", "")[:16].replace("T", " "),
                "status":    status,
                "home_score": home.get("score"),
                "away_score": away.get("score"),
                "conference": "Conference" if conf_note else None,
            })
    except Exception as e:
        print(f"  [NCAA/ESPN] Error: {e}")
    return games


# ─────────────────────────────────────────────────────────────────────────────
# NBL (Australia's top league — Rosetta API)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_nbl(target_date):
    date_str = target_date.strftime("%Y-%m-%d")
    # Determine correct season id — NBL season spans Oct-Apr, season id = start year
    season_id = target_date.year if target_date.month >= 10 else target_date.year - 1
    # Try current and next season id in case of overlap
    for s_id in [season_id, season_id + 1]:
        url = f"https://prod.rosetta.nbl.com.au/get/nbl/matches/in/season/{s_id}/all"
        headers = {
            "Origin": "https://nbl.com.au",
            "Referer": "https://nbl.com.au/",
            "User-Agent": "Mozilla/5.0",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            games = []
            for match in data.get("data", []):
                match_start = match.get("start_time", "")
                if match_start.split("T")[0] == date_str:
                    ht = match.get("home_team", {})
                    at = match.get("away_team", {})
                    games.append({
                        "game_id":   match.get("id"),
                        "home_team": ht.get("name"),
                        "away_team": at.get("name"),
                        "start_time": match_start[:16].replace("T", " "),
                        "status":    match.get("match_status", "Scheduled"),
                        "home_score": match.get("home_score"),
                        "away_score": match.get("away_score"),
                        "conference": None,
                    })
            if games:
                return games
        except Exception as e:
            print(f"  [NBL/Rosetta s={s_id}] Error: {e}")
    return []


# ─────────────────────────────────────────────────────────────────────────────
# NBL1 (Australian state leagues — api-basketball.com)
# ─────────────────────────────────────────────────────────────────────────────

# NBL1 Men's 5-conference league IDs on api-basketball.com
NBL1_CONFERENCES = {
    "Central": 212,
    "East":    215,
    "North":   207,
    "South":   209,
    "West":    214,
}

def _nbl1_season_for_date(d):
    return d.year if d.month >= 3 else d.year - 1

def fetch_nbl1(target_date):
    if not API_BASKETBALL_KEY:
        print("  [NBL1] API_BASKETBALL_KEY not set — skipping.")
        return []

    date_str = target_date.strftime("%Y-%m-%d")
    season = _nbl1_season_for_date(target_date)
    all_games = []

    for conf_name, league_id in NBL1_CONFERENCES.items():
        try:
            # api-basketball date filter sometimes unreliable for NBL1,
            # so fetch by season and filter locally (matches existing project approach)
            r = requests.get(
                f"{API_BASKETBALL_BASE}/games",
                headers=API_BASKETBALL_HEADERS,
                params={"league": league_id, "season": season},
                timeout=10,
            )
            response_games = r.json().get("response", [])
            for game in response_games:
                game_date_utc = game.get("date", "")[:10]
                # Also check Australian-local date
                ts = game.get("timestamp")
                if ts:
                    game_date_au = datetime.fromtimestamp(ts, tz=AU_TZ).strftime("%Y-%m-%d")
                else:
                    game_date_au = game_date_utc
                if game_date_utc == date_str or game_date_au == date_str:
                    g = parse_api_basketball_game(game, conference=conf_name)
                    all_games.append(g)
        except Exception as e:
            print(f"  [NBL1/{conf_name}] Error: {e}")

    return all_games


# ─────────────────────────────────────────────────────────────────────────────
# EuroLeague (euroleague.net XML API)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_euro(target_date):
    # EuroLeague season code: E + start year (e.g. E2025 for 2025-26)
    season_year = target_date.year if target_date.month >= 9 else target_date.year - 1
    season_code = f"E{season_year}"
    today_str = target_date.strftime("%b %d, %Y")  # e.g. "Mar 15, 2026"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml",
    }
    games = []
    try:
        sched_url = f"https://api-live.euroleague.net/v1/schedules?seasonCode={season_code}"
        sched_resp = requests.get(sched_url, headers=headers, timeout=10)
        sched_resp.raise_for_status()
        root = ET.fromstring(sched_resp.content)
        for item in root.findall("item"):
            gdate = item.find("date")
            if gdate is None or gdate.text != today_str:
                continue
            away = item.find("awayteam")
            home = item.find("hometeam")
            startime = item.find("startime")
            played_el = item.find("played")
            played = played_el is not None and played_el.text.lower() == "true"
            games.append({
                "game_id":    item.find("gamecode").text if item.find("gamecode") is not None else None,
                "home_team":  home.text if home is not None else "Unknown",
                "away_team":  away.text if away is not None else "Unknown",
                "start_time": startime.text if startime is not None else "TBD",
                "status":     "Final" if played else "Scheduled",
                "home_score": None,
                "away_score": None,
                "conference": None,
            })
    except Exception as e:
        print(f"  [EuroLeague] Error: {e}")
    return games


# ─────────────────────────────────────────────────────────────────────────────
# EuroCup (same euroleague.net XML API, different season code)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_eurocup(target_date):
    season_year = target_date.year if target_date.month >= 9 else target_date.year - 1
    season_code = f"U{season_year}"  # EuroCup uses "U" prefix
    today_str = target_date.strftime("%b %d, %Y")

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/xml"}
    games = []
    try:
        sched_url = f"https://api-live.euroleague.net/v1/schedules?seasonCode={season_code}"
        sched_resp = requests.get(sched_url, headers=headers, timeout=10)
        sched_resp.raise_for_status()
        root = ET.fromstring(sched_resp.content)
        for item in root.findall("item"):
            gdate = item.find("date")
            if gdate is None or gdate.text != today_str:
                continue
            away = item.find("awayteam")
            home = item.find("hometeam")
            startime = item.find("startime")
            played_el = item.find("played")
            played = played_el is not None and played_el.text.lower() == "true"
            games.append({
                "game_id":    item.find("gamecode").text if item.find("gamecode") is not None else None,
                "home_team":  home.text if home is not None else "Unknown",
                "away_team":  away.text if away is not None else "Unknown",
                "start_time": startime.text if startime is not None else "TBD",
                "status":     "Final" if played else "Scheduled",
                "home_score": None,
                "away_score": None,
                "conference": None,
            })
    except Exception as e:
        print(f"  [EuroCup] Error: {e}")
    return games


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

LEAGUE_FETCHERS = {
    "nba":     ("NBA",      fetch_nba),
    "ncaa":    ("NCAA D1",  fetch_ncaa),
    "nbl":     ("NBL",      fetch_nbl),
    "nbl1":    ("NBL1",     fetch_nbl1),
    "euro":    ("EuroLeague", fetch_euro),
    "eurocup": ("EuroCup",  fetch_eurocup),
}


def main():
    parser = argparse.ArgumentParser(description="Fetch today's basketball fixtures from all leagues")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format (default: today)")
    parser.add_argument(
        "--league",
        choices=list(LEAGUE_FETCHERS.keys()),
        default=None,
        help="Only fetch a specific league (default: all)",
    )
    parser.add_argument("--save", action="store_true", default=True,
                        help="Save results to data/basketball_fixtures_YYYY-MM-DD.json")
    args = parser.parse_args()

    target_date = get_target_date(args.date)
    date_str = target_date.strftime("%Y-%m-%d")

    leagues_to_run = {args.league: LEAGUE_FETCHERS[args.league]} if args.league else LEAGUE_FETCHERS

    print(f"\n{'='*60}")
    print(f"  BASKETBALL FIXTURES -- {date_str}")
    print(f"{'='*60}")

    all_results = {}
    total_games = 0

    for league_key, (league_name, fetcher) in leagues_to_run.items():
        games = fetcher(target_date)
        all_results[league_key] = {
            "league": league_name,
            "date": date_str,
            "count": len(games),
            "games": games,
        }
        total_games += len(games)

        print_league_header(league_name, len(games), date_str)

        if not games:
            print("  (no games today)")
            continue

        for g in games:
            score_str = ""
            if g.get("home_score") is not None and g.get("away_score") is not None:
                score_str = f"  {g['away_score']}-{g['home_score']}"

            conf_str = f"[{g['conference']}]" if g.get("conference") else ""
            status_str = g.get("status", "")
            time_str = g.get("start_time", "")

            # Format: Away @ Home  HH:MM  [Conference?]  [Status?]  Score?
            line = f"  {g['away_team']}  @  {g['home_team']}"
            if time_str:
                line += f"    {time_str}"
            if conf_str:
                line += f"  {conf_str}"
            if status_str and status_str not in ("Scheduled", ""):
                line += f"  [{status_str}]"
            if score_str:
                line += f"  {score_str}"
            print(line)

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total_games} game(s) across {len(leagues_to_run)} league(s)")
    print(f"{'='*60}\n")

    # Save JSON
    if args.save:
        os.makedirs("data", exist_ok=True)
        out_path = f"data/basketball_fixtures_{date_str}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print(f"Saved → {out_path}\n")


if __name__ == "__main__":
    main()
