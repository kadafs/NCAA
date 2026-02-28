import requests
import json
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

API_KEY  = os.getenv("API_BASKETBALL_KEY")   # Same provider — key works for both
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}

SUPPORTED_LEAGUES = {
    "epl":      {"id": 39,  "name": "Premier League",  "country": "England"},
    "la_liga":  {"id": 140, "name": "La Liga",          "country": "Spain"},
    "bundesliga":{"id": 78, "name": "Bundesliga",       "country": "Germany"},
    "serie_a":  {"id": 135, "name": "Serie A",          "country": "Italy"},
    "ligue_1":  {"id": 61,  "name": "Ligue 1",          "country": "France"},
    "a_league": {"id": 188, "name": "A-League",         "country": "Australia"},
}


def _get_current_season(league_id):
    """Returns the current (or most recent) season year for a league."""
    r = requests.get(f"{BASE_URL}/leagues", headers=HEADERS, params={"id": league_id})
    leagues = r.json().get("response", [])
    if not leagues:
        return None
    seasons = leagues[0].get("seasons", [])
    for s in sorted(seasons, key=lambda x: x.get("year", 0), reverse=True):
        if s.get("current"):
            return s["year"]
    return sorted(seasons, key=lambda x: x.get("year", 0), reverse=True)[0]["year"]


def _safe_get(url, headers, params, retries=3, delay=0.4):
    """Requests wrapper with retry logic and polite delay."""
    for attempt in range(retries):
        try:
            time.sleep(delay)
            r = requests.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 200:
                return r
            print(f"  HTTP {r.status_code} on attempt {attempt+1}, retrying...")
        except Exception as e:
            print(f"  Request error attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)   # exponential backoff: 1s, 2s, 4s
    return None


def _compute_league_averages(team_stats_list):
    """
    Calculates the league-wide average goals scored/conceded at home and away.
    Used to normalize Attack/Defense ratings.
    """
    home_goals_for, away_goals_for = [], []
    home_goals_against, away_goals_against = [], []

    for stats in team_stats_list:
        g = stats.get("_raw_goals", {})
        ph = stats.get("played_home", 1) or 1
        pa = stats.get("played_away", 1) or 1

        hgf = g.get("for_home", 0) / ph
        agf = g.get("for_away", 0) / pa
        hga = g.get("against_home", 0) / ph
        aga = g.get("against_away", 0) / pa

        if hgf > 0: home_goals_for.append(hgf)
        if agf > 0: away_goals_for.append(agf)
        if hga > 0: home_goals_against.append(hga)
        if aga > 0: away_goals_against.append(aga)

    n = len(home_goals_for) or 1
    return {
        "avg_home_goals_for":     round(sum(home_goals_for) / n, 3),
        "avg_away_goals_for":     round(sum(away_goals_for) / n, 3),
        "avg_home_goals_against": round(sum(home_goals_against) / n, 3),
        "avg_away_goals_against": round(sum(away_goals_against) / n, 3),
    }


def fetch_football_stats(league_code, season=None):
    """
    Fetches team stats for a football league from API-Football.
    Computes Attack/Defense ratings normalized to league average.
    Saves data/football/{league_code}_stats.json
    """
    if not API_KEY:
        print("ERROR: API_BASKETBALL_KEY not found in .env")
        return {}

    league_info = SUPPORTED_LEAGUES.get(league_code.lower())
    if not league_info:
        print(f"Unknown league: {league_code}. Supported: {list(SUPPORTED_LEAGUES.keys())}")
        return {}

    league_id = league_info["id"]
    if season is None:
        season = _get_current_season(league_id)
    if not season:
        print(f"Could not determine season for {league_code}")
        return {}

    print(f"Fetching {league_info['name']} (League {league_id}, Season {season})...")

    # Step 1: Get all teams in the league
    teams_r = requests.get(f"{BASE_URL}/teams", headers=HEADERS,
                           params={"league": league_id, "season": season})
    teams = teams_r.json().get("response", [])
    print(f"  {len(teams)} teams found.")

    raw_stats_list = []

    for team_entry in teams:
        team = team_entry.get("team", {})
        tid  = team.get("id")
        name = team.get("name")
        logo = team.get("logo", "")

        r = _safe_get(f"{BASE_URL}/teams/statistics", HEADERS,
                      {"team": tid, "league": league_id, "season": season})
        if r is None:
            print(f"  Could not fetch stats for {name} after retries, skipping.")
            continue
        stats = r.json().get("response", {})

        if not stats:
            print(f"  No stats for {name}, skipping.")
            continue

        games   = stats.get("fixtures", {})
        goals   = stats.get("goals",    {})
        form_str = stats.get("form", "")

        played_home = games.get("played", {}).get("home", 0)
        played_away = games.get("played", {}).get("away", 0)
        played_all  = games.get("played", {}).get("total", 0)

        wins_home = games.get("wins",  {}).get("home", 0)
        wins_away = games.get("wins",  {}).get("away", 0)
        draws_home = games.get("draws", {}).get("home", 0)
        draws_away = games.get("draws", {}).get("away", 0)

        goals_for_home  = goals.get("for",     {}).get("total", {}).get("home", 0)
        goals_for_away  = goals.get("for",     {}).get("total", {}).get("away", 0)
        goals_for_all   = goals.get("for",     {}).get("total", {}).get("total", 0)
        goals_ag_home   = goals.get("against", {}).get("total", {}).get("home", 0)
        goals_ag_away   = goals.get("against", {}).get("total", {}).get("away", 0)
        goals_ag_all    = goals.get("against", {}).get("total", {}).get("total", 0)

        clean_sheets = stats.get("clean_sheet", {}).get("total", 0)
        failed_score = stats.get("failed_to_score", {}).get("total", 0)
        btts_count   = played_all - clean_sheets - failed_score   # games where both scored

        pgf_home = goals_for_home  / played_home if played_home else 0
        pga_home = goals_ag_home   / played_home if played_home else 0
        pgf_away = goals_for_away  / played_away if played_away else 0
        pga_away = goals_ag_away   / played_away if played_away else 0
        pgf_all  = goals_for_all   / played_all  if played_all  else 0
        pga_all  = goals_ag_all    / played_all  if played_all  else 0

        win_pct  = (wins_home + wins_away) / played_all if played_all else 0
        form_wins = form_str.upper().count("W") if form_str else 0
        form_draws = form_str.upper().count("D") if form_str else 0

        streak_btts = 0   # will be filled in after league averages are set

        raw_stats_list.append({
            "name":      name,
            "team_id":   tid,
            "logo":      logo,
            "league_id": league_id,
            "season":    season,
            # Played
            "played_home": played_home,
            "played_away": played_away,
            "played_all":  played_all,
            # Goals
            "goals_for_home": goals_for_home,
            "goals_for_away": goals_for_away,
            "goals_for_all":  goals_for_all,
            "goals_ag_home":  goals_ag_home,
            "goals_ag_away":  goals_ag_away,
            "goals_ag_all":   goals_ag_all,
            # Per game rates
            "pgf_home": round(pgf_home, 3),
            "pgf_away": round(pgf_away, 3),
            "pgf_all":  round(pgf_all, 3),
            "pga_home": round(pga_home, 3),
            "pga_away": round(pga_away, 3),
            "pga_all":  round(pga_all, 3),
            # W/D/L
            "wins_home":  wins_home,
            "wins_away":  wins_away,
            "draws_home": draws_home,
            "draws_away": draws_away,
            "win_pct":    round(win_pct, 3),
            # BTTS tracking
            "clean_sheets": clean_sheets,
            "failed_score": failed_score,
            "btts_count":   btts_count,
            "btts_rate":    round(btts_count / played_all, 3) if played_all else 0,
            # Form
            "form":       form_str,
            "form_wins":  form_wins,
            "form_draws": form_draws,
            # Raw goals for league average computation
            "_raw_goals": {
                "for_home":     goals_for_home,
                "for_away":     goals_for_away,
                "against_home": goals_ag_home,
                "against_away": goals_ag_away,
            }
        })

        print(f"    {name}: {pgf_all:.2f} GF/g | {pga_all:.2f} GA/g | BTTS {btts_count}/{played_all}")

    if not raw_stats_list:
        print("No stats collected.")
        return {}

    # Step 2: Compute league averages
    league_avgs = _compute_league_averages(raw_stats_list)
    avg_home = league_avgs["avg_home_goals_for"] or 1.0
    avg_away = league_avgs["avg_away_goals_for"] or 1.0

    print(f"\n  League averages: {avg_home:.2f} home goals/g | {avg_away:.2f} away goals/g")

    # Step 3: Compute Attack / Defense Ratings + clean up output
    final_stats = {}
    for entry in raw_stats_list:
        pgf_home = entry["pgf_home"]
        pgf_away = entry["pgf_away"]
        pga_home = entry["pga_home"]
        pga_away = entry["pga_away"]

        # Attack rating: how many goals does this team score vs league average?
        ar_home = pgf_home / avg_home if avg_home else 1.0
        ar_away = pgf_away / avg_away if avg_away else 1.0
        ar_all  = (ar_home + ar_away) / 2

        # Defense rating: how many goals does this team concede vs league average?
        # Higher DR = weaker defense (concedes more than average)
        dr_home = pga_home / avg_home if avg_home else 1.0  # vs home attacker avg
        dr_away = pga_away / avg_away if avg_away else 1.0  # vs away attacker avg
        dr_all  = (dr_home + dr_away) / 2

        name = entry["name"]
        entry["attack_rating_home"]    = round(ar_home, 4)
        entry["attack_rating_away"]    = round(ar_away, 4)
        entry["attack_rating_all"]     = round(ar_all,  4)
        entry["defense_rating_home"]   = round(dr_home, 4)
        entry["defense_rating_away"]   = round(dr_away, 4)
        entry["defense_rating_all"]    = round(dr_all,  4)
        entry["league_avg_home_goals"] = avg_home
        entry["league_avg_away_goals"] = avg_away

        # Remove raw goals (internal only)
        entry.pop("_raw_goals", None)

        final_stats[name] = entry

    # Step 4: Save
    os.makedirs("data/football", exist_ok=True)
    out_path = f"data/football/{league_code}_stats.json"
    payload = {
        "league":       league_info["name"],
        "league_code":  league_code,
        "league_id":    league_id,
        "season":       season,
        "fetched_at":   datetime.utcnow().isoformat(),
        "league_averages": league_avgs,
        "teams":        final_stats
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nSaved {len(final_stats)} teams to {out_path}")
    return payload


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch football team stats from API-Football")
    parser.add_argument("--league", required=True, choices=list(SUPPORTED_LEAGUES.keys()),
                        help="League code (e.g. epl, la_liga, a_league)")
    parser.add_argument("--season", type=int, help="Season year (e.g. 2024)")
    args = parser.parse_args()
    fetch_football_stats(args.league, season=args.season)
