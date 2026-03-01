import requests
import json
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

API_KEY  = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}

SUPPORTED_LEAGUES = {
    "epl":      {"id": 39,  "name": "Premier League",  "country": "England"},
    "la_liga":  {"id": 140, "name": "La Liga",          "country": "Spain"},
    "bundesliga":{"id": 78, "name": "Bundesliga",       "country": "Germany"},
    "serie_a":  {"id": 135, "name": "Serie A",          "country": "Italy"},
    "ligue_1":  {"id": 61,  "name": "Ligue 1",          "country": "France"},
    "a_league": {"id": 188, "name": "A-League",         "country": "Australia"},
    "hk_1st": {"id": 381, "name": "Hong Kong 1st Division", "country": "Hong-Kong"},
    "eng_dev_2": {"id": 703, "name": "Professional Development League", "country": "England"},
    "eng_pl_2": {"id": 702, "name": "Premier League 2", "country": "England"},
    "wales_champ": {"id": 111, "name": "FAW Championship", "country": "Wales"},
    "aus_landesliga": {"id": 228, "name": "Landesliga Salzburg", "country": "Austria"},
    "scot_highland": {"id": 730, "name": "Highland League", "country": "Scotland"},
    "scot_lowland": {"id": 731, "name": "Lowland League", "country": "Scotland"},
    "ind_ileague": {"id": 324, "name": "I-League", "country": "India"},
    "cro_1nl": {"id": 211, "name": "First NL", "country": "Croatia"},
    "swe_div1_norra": {"id": 563, "name": "Ettan Norra", "country": "Sweden"},
    "uefa_cl": {"id": 2, "name": "UEFA Champions League", "country": "World"},
    "nor_div1": {"id": 104, "name": "1. Division", "country": "Norway"},
    "den_superliga": {"id": 119, "name": "Superliga", "country": "Denmark"},
    "ger_reg_west": {"id": 87, "name": "Regionalliga West", "country": "Germany"},
    "eng_isthmian": {"id": 58, "name": "Isthmian Premier", "country": "England"},
    "lat_1liga": {"id": 364, "name": "1. Liga", "country": "Latvia"},
    "crc_segunda": {"id": 163, "name": "Liga de Ascenso", "country": "Costa-Rica"},
    "ned_eredivisie": {"id": 88, "name": "Eredivisie", "country": "Netherlands"},
    "scot_prem": {"id": 179, "name": "Premiership", "country": "Scotland"},
    "ban_pl": {"id": 398, "name": "Premier League", "country": "Bangladesh"},
    "swe_damallsvenskan": {"id": 549, "name": "Damallsvenskan", "country": "Sweden"},
    "par_primera_ap": {"id": 250, "name": "Division Profesional Apertura", "country": "Paraguay"},
    "usa_mls": {"id": 253, "name": "Major League Soccer", "country": "USA"},
    "ven_primera": {"id": 299, "name": "Primera Division", "country": "Venezuela"},
    "spa_tercera_6": {"id": 444, "name": "Tercera RFEF Group 6", "country": "Spain"},
    "hon_liga_nac": {"id": 234, "name": "Liga Nacional", "country": "Honduras"},
    "spa_tercera_18": {"id": 456, "name": "Tercera RFEF Group 18", "country": "Spain"},
    "ecu_primera_b": {"id": 243, "name": "Liga Pro Serie B", "country": "Ecuador"},
    "arg_nacional_b": {"id": 129, "name": "Primera Nacional", "country": "Argentina"},
    "arg_primera": {"id": 128, "name": "Liga Profesional", "country": "Argentina"},
    "ita_serie_b": {"id": 136, "name": "Serie B", "country": "Italy"},
    "col_primera_a": {"id": 239, "name": "Primera A", "country": "Colombia"},
    "arg_primera_b": {"id": 131, "name": "Primera B Metropolitana", "country": "Argentina"},
    "fra_national": {"id": 63, "name": "National 1", "country": "France"},
    "egy_prem": {"id": 233, "name": "Premier League", "country": "Egypt"},
    "uru_apertura": {"id": 268, "name": "Primera Div Apertura", "country": "Uruguay"}
}


def fetch_football_schedule(league_code, date_obj=None, season=None):
    """
    Fetches today's fixtures for a football league from API-Football.
    The v3 football API date filter works reliably (unlike basketball).
    Saves: data/football/{league_code}_fixtures.json
    """
    if not API_KEY:
        print("ERROR: API_BASKETBALL_KEY not found in .env")
        return []

    league_info = SUPPORTED_LEAGUES.get(league_code.lower())
    if not league_info:
        print(f"Unknown league: {league_code}")
        return []

    league_id = league_info["id"]
    date_str  = (date_obj or datetime.utcnow()).strftime("%Y-%m-%d")

    print(f"Fetching {league_code.upper()} fixtures for {date_str} (League {league_id})...")

    params = {"league": league_id, "date": date_str}
    if season:
        params["season"] = season

    r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params=params)
    fixtures = r.json().get("response", [])

    if not fixtures:
        print(f"  No fixtures found for {date_str}.")
        # Still save an empty file so populate.py doesn't crash
        os.makedirs("data/football", exist_ok=True)
        out_path = f"data/football/{league_code}_fixtures.json"
        with open(out_path, "w") as f:
            json.dump([], f)
        return []

    matchups = []
    for fix in fixtures:
        fixture   = fix.get("fixture", {})
        teams     = fix.get("teams",   {})
        league    = fix.get("league",  {})
        score     = fix.get("score",   {})
        goals     = fix.get("goals",   {})

        fid       = fixture.get("id")
        status    = fixture.get("status", {}).get("short", "NS")
        kickoff   = fixture.get("date", "")

        home_team = teams.get("home", {})
        away_team = teams.get("away", {})

        home_name = home_team.get("name")
        away_name = away_team.get("name")
        home_logo = home_team.get("logo", "")
        away_logo = away_team.get("logo", "")

        home_winner = home_team.get("winner")  # True / False / None
        away_winner = away_team.get("winner")

        # Result (if played)
        home_goals = goals.get("home")
        away_goals = goals.get("away")

        is_completed = status in ("FT", "AET", "PEN")
        btts_result = None
        draw_result = None
        if is_completed and home_goals is not None and away_goals is not None:
            btts_result  = (home_goals > 0 and away_goals > 0)
            draw_result  = (home_goals == away_goals)

        matchups.append({
            "fixture_id":    fid,
            "status":        status,
            "kickoff":       kickoff,
            "date":          date_str,
            "league_id":     league_id,
            "league_code":   league_code,
            "home_team":     home_name,
            "away_team":     away_name,
            "home_logo":     home_logo,
            "away_logo":     away_logo,
            "home_goals":    home_goals,
            "away_goals":    away_goals,
            "is_completed":  is_completed,
            "btts_result":   btts_result,
            "draw_result":   draw_result,
        })

        print(f"  [{status}] {away_name} @ {home_name} ({kickoff})")

    # Save
    os.makedirs("data/football", exist_ok=True)
    out_path = f"data/football/{league_code}_fixtures.json"
    with open(out_path, "w") as f:
        json.dump(matchups, f, indent=2)

    print(f"\nSaved {len(matchups)} fixtures to {out_path}")
    return matchups


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch football fixtures from API-Football")
    parser.add_argument("--league",  required=True, choices=list(SUPPORTED_LEAGUES.keys()))
    parser.add_argument("--date",    help="Date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--season",  type=int)
    args = parser.parse_args()

    date_obj = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None
    fetch_football_schedule(args.league, date_obj=date_obj, season=args.season)
