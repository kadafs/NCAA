import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_BASKETBALL_KEY")
if not API_KEY:
    print("API_BASKETBALL_KEY not found in .env")
    exit(1)

HEADERS = {'x-apisports-key': API_KEY}
BASE_URL = 'https://v3.football.api-sports.io'

# The curated list of High-Priority "Tier 1 and Tier 2" global leagues.
PRIORITY_LEAGUES = {
    # Top 5 Europe + 2nd Divisions
    39, 40,   # English Premier League, Championship
    140, 141, # Spain La Liga, Segunda
    135, 136, # Italy Serie A, Serie B
    78, 79,   # Germany Bundesliga, 2. Bundesliga
    61, 62,   # France Ligue 1, Ligue 2
    
    # European Tournaments
    2, 3, 848, # UCL, Europa, Conference Leagues
    
    # Americas
    253, 254, # MLS, USL
    71,       # Brazil Serie A
    262,      # Liga MX
    128,      # Argentina Liga Profesional
    
    # Top European Tier 2
    88,       # Netherlands Eredivisie
    94,       # Portugal Primeira Liga
    119,      # Denmark Superliga
    144,      # Belgium Pro League
    203,      # Turkey Super Lig
    103,      # Norway Eliteserien
    113,      # Sweden Allsvenskan
}

DATA_DIR = os.path.join("data", "football", "props")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_endpoint(endpoint: str, league_id: int, season: int) -> list:
    url = f"{BASE_URL}/{endpoint}"
    params = {'league': league_id, 'season': season}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("response", [])
    except Exception as e:
        print(f"Error fetching {endpoint} for league {league_id}: {e}")
        return []

def main():
    for lid in PRIORITY_LEAGUES:
        print(f"Processing league {lid}...")
        
        # Get current season
        try:
            r = requests.get(f"{BASE_URL}/leagues", headers=HEADERS, params={"id": lid, "current": "true"}, timeout=10)
            league_data = r.json().get("response", [])
            if not league_data:
                continue
            season = league_data[0]["seasons"][0]["year"]
        except Exception:
            season = 2024

        topscorers = fetch_endpoint("players/topscorers", lid, season)
        topassists = fetch_endpoint("players/topassists", lid, season)
        topyellows = fetch_endpoint("players/topyellowcards", lid, season)

        # Group players by team ID
        team_props = {}

        def process_players(player_list, stat_type):
            for p in player_list:
                player_info = p.get("player", {})
                stats_info = p.get("statistics", [{}])[0]
                team = stats_info.get("team", {})
                team_id = team.get("id")
                
                if not team_id:
                    continue

                if team_id not in team_props:
                    team_props[team_id] = {
                        "team_id": team_id,
                        "team_name": team.get("name"),
                        "topscorers": [],
                        "topassists": [],
                        "topyellows": []
                    }

                # Extract relevant stats
                games = stats_info.get("games", {}).get("appearences", 0)
                if not games: games = 1 # Avoid div by zero

                goals = stats_info.get("goals", {}).get("total", 0) or 0
                shots = stats_info.get("shots", {}).get("total", 0) or 0
                shots_on = stats_info.get("shots", {}).get("on", 0) or 0
                assists = stats_info.get("goals", {}).get("assists", 0) or 0
                yellows = stats_info.get("cards", {}).get("yellow", 0) or 0
                reds = stats_info.get("cards", {}).get("red", 0) or 0

                simplified_player = {
                    "id": player_info.get("id"),
                    "name": player_info.get("name"),
                    "photo": player_info.get("photo"),
                    "games": games,
                    "goals": goals,
                    "shots": shots,
                    "shots_on": shots_on,
                    "assists": assists,
                    "yellows": yellows,
                    "reds": reds,
                    "goals_per_game": round(goals / games, 2),
                    "shots_on_per_game": round(shots_on / games, 2),
                    "assists_per_game": round(assists / games, 2),
                    "cards_per_game": round((yellows + reds) / games, 2)
                }

                existing = [x["id"] for x in team_props[team_id][stat_type]]
                if simplified_player["id"] not in existing:
                    team_props[team_id][stat_type].append(simplified_player)

        process_players(topscorers, "topscorers")
        process_players(topassists, "topassists")
        process_players(topyellows, "topyellows")

        # Save each team's props to a JSON file
        for team_id, props in team_props.items():
            out_path = os.path.join(DATA_DIR, f"team_{team_id}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(props, f, indent=2)

        print(f"  -> Saved props for {len(team_props)} teams in League {lid}")
        time.sleep(1)

    print("\nFinished building player props for all priority leagues!")

if __name__ == "__main__":
    main()
