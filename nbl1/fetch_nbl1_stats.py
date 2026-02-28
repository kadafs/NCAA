import requests
import json
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# NBL1 Men's Conference League IDs
NBL1_CONFERENCES = {
    "Central": 212,
    "East": 215,
    "North": 207,
    "South": 209,
    "West": 214
}

def _get_current_season(league_id):
    """Finds the most recent season with data for a given league."""
    r = requests.get(f"{BASE_URL}/leagues", headers=HEADERS, params={"id": league_id})
    leagues = r.json().get("response", [])
    if not leagues:
        return None

    seasons = leagues[0].get("seasons", [])
    seasons.sort(key=lambda s: s.get("season", 0), reverse=True)

    for s in seasons:
        if s.get("current"):
            return s["season"]

    return seasons[0]["season"] if seasons else None


def _parse_form(form_str):
    """Count wins in form string (e.g. 'WWLWW' -> 4)."""
    if not form_str:
        return 2  # neutral default
    return form_str.upper().count("W")


def fetch_nbl1_stats(season=None):
    """
    Fetches NBL1 team stats for all 5 conferences via API-Basketball.
    Stores both aggregate and home/away split stats for Full Mode sharp layer.
    """
    if not API_KEY:
        print("ERROR: API_BASKETBALL_KEY not found in .env")
        return {}

    combined_stats = {}

    for conf_name, league_id in NBL1_CONFERENCES.items():
        if season is None:
            s = _get_current_season(league_id)
            if not s:
                print(f"  No season found for NBL1 {conf_name}, skipping.")
                continue
        else:
            s = season

        print(f"  Fetching NBL1 {conf_name} (League {league_id}, Season {s})...")

        try:
            # 1. Standings — W/L, points for/against, form string
            r_standings = requests.get(f"{BASE_URL}/standings", headers=HEADERS,
                                       params={"league": league_id, "season": s})
            standings_groups = r_standings.json().get("response", [])

            standings_map = {}
            if standings_groups:
                for team_standing in standings_groups[0]:
                    t = team_standing.get("team", {})
                    tid = t.get("id")
                    name = t.get("name")
                    if not tid or not name:
                        continue

                    games = team_standing.get("games", {})
                    points = team_standing.get("points", {})
                    played = games.get("played", 0)
                    wins = games.get("win", {}).get("total", 0)
                    losses = games.get("lose", {}).get("total", 0)
                    pts_for = points.get("for", 0)
                    pts_against = points.get("against", 0)

                    standings_map[tid] = {
                        "name": name,
                        "logo": t.get("logo", ""),
                        "wins": wins,
                        "losses": losses,
                        "played": played,
                        "points_for": pts_for,
                        "points_against": pts_against,
                        "form": team_standing.get("form", "")  # e.g. "WWLWW"
                    }

            # 2. Per-team statistics — full home/away splits
            teams_r = requests.get(f"{BASE_URL}/teams", headers=HEADERS,
                                   params={"league": league_id, "season": s})
            teams_list = teams_r.json().get("response", [])

            for team in teams_list:
                tid = team.get("id")
                name = team.get("name")
                logo = team.get("logo", "")

                stats_r = requests.get(f"{BASE_URL}/statistics", headers=HEADERS,
                                       params={"team": tid, "league": league_id, "season": s})
                stats = stats_r.json().get("response", {})

                if not stats:
                    continue

                pts_data = stats.get("points", {})
                games_data = stats.get("games", {})

                # --- Aggregate stats ---
                ppg_all  = float(pts_data.get("for",     {}).get("average", {}).get("all",  0) or 0)
                papg_all = float(pts_data.get("against", {}).get("average", {}).get("all",  0) or 0)
                played   = games_data.get("played", {}).get("all", 0)
                wins_all = games_data.get("wins",   {}).get("all", {}).get("total", 0)
                loses_all= games_data.get("loses",  {}).get("all", {}).get("total", 0)

                # --- Home/Away splits ---
                ppg_home  = float(pts_data.get("for",     {}).get("average", {}).get("home", 0) or 0)
                ppg_away  = float(pts_data.get("for",     {}).get("average", {}).get("away", 0) or 0)
                papg_home = float(pts_data.get("against", {}).get("average", {}).get("home", 0) or 0)
                papg_away = float(pts_data.get("against", {}).get("average", {}).get("away", 0) or 0)
                played_home = games_data.get("played", {}).get("home", 0)
                played_away = games_data.get("played", {}).get("away", 0)
                wins_home   = games_data.get("wins",   {}).get("home", {}).get("total", 0)
                wins_away   = games_data.get("wins",   {}).get("away", {}).get("total", 0)

                # --- Derived pace & ratings ---
                total_ppg = ppg_all + papg_all
                est_pace = 72.0 * (total_ppg / 190.0) if total_ppg > 0 else 72.0
                off_rating = (ppg_all  / est_pace) * 100 if est_pace > 0 else 100.0
                def_rating = (papg_all / est_pace) * 100 if est_pace > 0 else 100.0

                # Home/away pace estimates (from venue PPG)
                total_ppg_home = ppg_home + papg_home
                total_ppg_away = ppg_away + papg_away
                pace_home = 72.0 * (total_ppg_home / 190.0) if total_ppg_home > 0 else est_pace
                pace_away = 72.0 * (total_ppg_away / 190.0) if total_ppg_away > 0 else est_pace

                # Win percentages
                win_pct      = wins_all  / played      if played      > 0 else 0.5
                win_pct_home = wins_home / played_home if played_home > 0 else 0.5
                win_pct_away = wins_away / played_away if played_away > 0 else 0.5

                standing = standings_map.get(tid, {})
                form_str = standing.get("form", "")
                form_wins = _parse_form(form_str)

                combined_stats[name] = {
                    # Identity
                    "conference": conf_name,
                    "team_id": tid,
                    "logo": logo or standing.get("logo", ""),

                    # Core ratings (aggregate)
                    "offensive_rating":     round(off_rating, 1),
                    "defensive_rating":     round(def_rating, 1),
                    "pace":                 round(est_pace, 1),
                    "points_for_average":   ppg_all,
                    "points_against_average": papg_all,
                    "wins":                 wins_all,
                    "losses":               loses_all,
                    "played":               played,
                    "points_for":           standing.get("points_for",     int(ppg_all  * played)),
                    "points_against":       standing.get("points_against", int(papg_all * played)),
                    "win_pct":              round(win_pct, 3),

                    # Home/Away SPLITS (used by Full Mode sharp layer)
                    "ppg_home":       ppg_home,
                    "ppg_away":       ppg_away,
                    "papg_home":      papg_home,
                    "papg_away":      papg_away,
                    "pace_home":      round(pace_home, 1),
                    "pace_away":      round(pace_away, 1),
                    "wins_home":      wins_home,
                    "wins_away":      wins_away,
                    "played_home":    played_home,
                    "played_away":    played_away,
                    "win_pct_home":   round(win_pct_home, 3),
                    "win_pct_away":   round(win_pct_away, 3),

                    # Form momentum (last 5 games)
                    "form":           form_str,
                    "form_wins":      form_wins   # int 0-5
                }

            conf_count = len([v for v in combined_stats.values() if v["conference"] == conf_name])
            print(f"    -> {conf_count} teams processed")

        except Exception as e:
            print(f"  Error fetching NBL1 {conf_name}: {e}")
            continue

    print(f"\nTotal: {len(combined_stats)} NBL1 teams across all conferences.")

    os.makedirs("data", exist_ok=True)
    with open("data/nbl1_stats.json", "w") as f:
        json.dump(combined_stats, f, indent=4)

    return combined_stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch NBL1 team stats from API-Basketball")
    parser.add_argument("--season", type=int, help="Season year (e.g. 2024)")
    parser.add_argument("--conf",   help="Single conference to fetch (Central/East/North/South/West)")
    args = parser.parse_args()

    if args.conf:
        original = NBL1_CONFERENCES.copy()
        NBL1_CONFERENCES.clear()
        if args.conf in original:
            NBL1_CONFERENCES[args.conf] = original[args.conf]
        else:
            print(f"Unknown conference: {args.conf}. Valid: {list(original.keys())}")
            sys.exit(1)

    fetch_nbl1_stats(season=args.season)
