import json
import os
import time
import requests
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguedashteamstats
import sys

# Root addition for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.nba_api_client import RobustNBAClient

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "nba_stats.json")

def fetch_espn_standings_api():
    """
    Fetches basic NBA team stats from ESPN's hidden API.
    Provides team names, PPG, and Opp PPG.
    """
    print("Attempting ESPN Standings API for NBA stats...")
    url = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
    try:
        resp = requests.get(url, timeout=20)
        data = resp.json()
        
        ratings = {}
        # The structure is nested: children -> standings -> entries
        # children[0] is Eastern Conference, children[1] is Western Conference
        for conf in data.get('children', []):
            standings = conf.get('standings', {})
            for entry in standings.get('entries', []):
                team_data = entry.get('team', {})
                name = team_data.get('displayName')
                abbrev = team_data.get('abbreviation')
                
                stats_list = entry.get('stats', [])
                off_raw = 115.0
                def_raw = 115.0
                
                for s in stats_list:
                    if s.get('name') == 'avgPointsFor':
                        off_raw = s.get('value', 115.0)
                    elif s.get('name') == 'avgPointsAgainst':
                        def_raw = s.get('value', 115.0)
                
                if name:
                    ratings[name] = {
                        "pts": off_raw,
                        "fg3a": 35.0, # Approximate/Default
                        "adj_off": off_raw, 
                        "adj_def": def_raw,
                        "adj_t": 100.0,
                        "four_factors": {"efg": 52.0, "tov": 14.0, "orb": 25.0, "ftr": 20.0},
                        "allowed": {"pts": def_raw, "ast": 25.0, "reb": 44.0, "fg3a": 35.0},
                        "conf": "NBA",
                        "abbrev": abbrev
                    }
        
        if ratings:
            print(f"ESPN Standings API successful for {len(ratings)} teams.")
            return ratings
        return None
    except Exception as e:
        print(f"ESPN Standings API failed: {e}")
        return None

def fetch_espn_fallback():
    """
    Scrapes ESPN for basic NBA team stats as a fallback when stats.nba.com is blocked.
    Now prioritizes the Standings API.
    """
    # 1. Try Standings API first
    ratings = fetch_espn_standings_api()
    if ratings:
        return ratings

    # 2. Scraper fallback (Legacy/Secondary)
    print("Attempting secondary ESPN scraping fallback...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    diff_url = "https://www.espn.com/nba/stats/team/_/view/differential"
    
    try:
        resp = requests.get(diff_url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # ESPN stats pages are often split into names table and stats table
        all_tables = soup.find_all('table')
        if len(all_tables) < 2:
            return None
            
        name_table = all_tables[0]
        stat_table = all_tables[1]
        
        # Try to find team links
        names = []
        for a in name_table.find_all('a'):
            text = a.get_text(strip=True)
            if text and not text.isdigit() and len(text) > 2:
                names.append(text)
        
        if not names: # Fallback to td text if no links
            names = [td.get_text(strip=True) for td in name_table.find_all('td') if td.get_text(strip=True) and not td.get_text(strip=True).isdigit()]
        
        rows = stat_table.find_all('tr')[1:] # Skip header
        ratings = {}
        for name, row in zip(names, rows):
            cols = [td.get_text(strip=True) for td in row.find_all('td')]
            if len(cols) >= 3:
                try:
                    off_raw = float(cols[1])
                    def_raw = float(cols[2])
                    ratings[name] = {
                        "pts": off_raw,
                        "fg3a": 35.0,
                        "adj_off": off_raw, 
                        "adj_def": def_raw,
                        "adj_t": 100.0,
                        "four_factors": {"efg": 52.0, "tov": 14.0, "orb": 25.0, "ftr": 20.0},
                        "allowed": {"pts": def_raw, "ast": 25.0, "reb": 44.0, "fg3a": 35.0},
                        "conf": "NBA"
                    }
                except (ValueError, IndexError):
                    continue
        return ratings if ratings else None
    except Exception as e:
        print(f"Secondary scraping fallback failed: {e}")
        return None

def fetch_nba_complete_stats():
    print("Fetching NBA Complete Stats from official API (with retries)...")
    
    processed_data = None
    
    try:
        # Attempting official API
        # 1. Fetch Base Stats
        base_stats = RobustNBAClient.call_endpoint(
            leaguedashteamstats.LeagueDashTeamStats,
            measure_type_detailed_defense='Base',
            per_mode_detailed='PerGame',
            season='2025-26',
            season_type_all_star='Regular Season',
            timeout=15
        )

        # 2. Fetch Advanced Stats
        advanced_stats = RobustNBAClient.call_endpoint(
            leaguedashteamstats.LeagueDashTeamStats,
            measure_type_detailed_defense='Advanced',
            season='2025-26',
            season_type_all_star='Regular Season',
            timeout=15
        )

        # 3. Fetch Opponent Stats
        opponent_stats = RobustNBAClient.call_endpoint(
            leaguedashteamstats.LeagueDashTeamStats,
            measure_type_detailed_defense='Opponent',
            per_mode_detailed='PerGame',
            season='2025-26',
            season_type_all_star='Regular Season',
            timeout=15
        )

        # Extract data (Simplified for this snippet)
        h_base = base_stats['resultSets'][0]['headers']
        r_base = base_stats['resultSets'][0]['rowSet']
        h_adv = advanced_stats['resultSets'][0]['headers']
        r_adv = advanced_stats['resultSets'][0]['rowSet']
        h_opp = opponent_stats['resultSets'][0]['headers']
        r_opp = opponent_stats['resultSets'][0]['rowSet']

        processed_data = {}

        for row in r_adv:
            row_dict_adv = dict(zip(h_adv, row))
            team_name = row_dict_adv['TEAM_NAME']
            
            row_dict_base = next((dict(zip(h_base, rb)) for rb in r_base if rb[h_base.index('TEAM_NAME')] == team_name), {})
            row_dict_opp = next((dict(zip(h_opp, ro)) for ro in r_opp if ro[h_opp.index('TEAM_NAME')] == team_name), {})

            fga = row_dict_base.get('FGA', 1)
            fta = row_dict_base.get('FTA', 0)
            ftr = (fta / fga * 100) if fga > 0 else 0

            processed_data[team_name] = {
                "pts": row_dict_base.get('PTS', 115.0),
                "fg3a": row_dict_base.get('FG3A', 35.0),
                "adj_off": row_dict_adv['OFF_RATING'],
                "adj_def": row_dict_adv['DEF_RATING'],
                "adj_t": row_dict_adv['PACE'],
                "four_factors": {
                    "efg": row_dict_adv.get('EFG_PCT', 0) * 100,
                    "tov": row_dict_adv.get('TM_TOV_PCT', 0) * 100,
                    "orb": row_dict_adv.get('OREB_PCT', 0) * 100,
                    "ftr": ftr
                },
                "allowed": {
                    "pts": row_dict_opp.get('OPP_PTS', 115.0),
                    "ast": row_dict_opp.get('OPP_AST', 25.0),
                    "reb": row_dict_opp.get('OPP_REB', 44.0),
                    "fg3a": row_dict_opp.get('OPP_FG3A', 35.0)
                },
                "conf": "NBA"
            }

    except Exception as e:
        print(f"NBA API failed: {e}")
        processed_data = fetch_espn_fallback()

    if processed_data:
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(processed_data, f, indent=2)
        print(f"Successfully saved stats for {len(processed_data)} NBA teams.")
        return True
    
    return False

if __name__ == "__main__":
    fetch_nba_complete_stats()
