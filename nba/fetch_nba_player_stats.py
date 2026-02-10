import json
import os
import sys
from nba_api.stats.endpoints import leaguedashplayerstats, fantasywidget

# Root addition for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.nba_api_client import RobustNBAClient

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "nba_player_stats.json")

# Shared headers for NBA API
NBA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'DNT': '1',
    'Connection': 'keep-alive',
}

def fetch_player_positions():
    """Fetches player positions using FantasyWidget."""
    print("Fetching NBA Player Positions...")
    try:
        data = RobustNBAClient.call_endpoint(
            fantasywidget.FantasyWidget,
            todays_players='N',
            timeout=30
        )
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        pos_map = {}
        for row in rows:
            d = dict(zip(headers, row))
            pos_map[d['PLAYER_ID']] = d.get('PLAYER_POSITION', 'G')
        return pos_map
    except Exception as e:
        print(f"Warning: Could not fetch positions ({e}). Using defaults.")
        return {}

def fetch_player_data(last_n=0):
    """Fetches player stats for the current season."""
    print(f"Fetching {'Season' if last_n==0 else f'Last {last_n}'} NBA Player Stats...")
    try:
        data = RobustNBAClient.call_endpoint(
            leaguedashplayerstats.LeagueDashPlayerStats,
            last_n_games=last_n,
            per_mode_detailed='PerGame',
            season='2025-26',
            season_type_all_star='Regular Season',
            timeout=30
        )
        
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        processed = {}
        for row in rows:
            d = dict(zip(headers, row))
            processed[d['PLAYER_ID']] = {
                "name": d['PLAYER_NAME'],
                "team": d['TEAM_ABBREVIATION'],
                "gp": d['GP'],
                "min": d['MIN'],
                "pts": d['PTS'],
                "reb": d['REB'],
                "ast": d['AST'],
                "stl": d['STL'],
                "blk": d['BLK'],
                "tov": d['TOV'],
                "fg3m": d['FG3M'],
                "fgm": d['FGM'],
                "fga": d['FGA'],
                "ftm": d['FTM'],
                "fta": d['FTA']
            }
        return processed
    except Exception as e:
        print(f"Error fetching player data (last_n={last_n}): {e}")
        return {}

def fetch_nba_player_stats():
    """Main entry point to fetch and merge NBA player stats."""
    print("Fetching NBA Player Stats (v1.2) from official API...")
    
    try:
        # 1. Fetch Season Averages
        season_stats = fetch_player_data(0)
        if not season_stats:
            print("Failed to fetch seasonal stats. Aborting.")
            return False
            
        # 2. Fetch Last 5 Games
        recent_stats = fetch_player_data(5)
        
        # 3. Fetch Positions
        pos_map = fetch_player_positions()
        
        # 4. Merge into v1.2 Prop Structure
        merged = []
        for pid, s_data in season_stats.items():
            r_data = recent_stats.get(pid, s_data)
            p_pos = pos_map.get(pid, "G")
            
            merged.append({
                "id": pid,
                "name": s_data['name'],
                "team": s_data['team'],
                "pos": p_pos,
                "gp": s_data['gp'],
                "seasonal": {
                    "min": s_data['min'],
                    "pts": s_data['pts'],
                    "reb": s_data['reb'],
                    "ast": s_data['ast'],
                    "stl": s_data['stl'],
                    "blk": s_data['blk'],
                    "tov": s_data['tov'],
                    "3pm": s_data['fg3m'],
                    "fgm": s_data['fgm'],
                    "fga": s_data['fga'],
                    "ftm": s_data['ftm'],
                    "fta": s_data['fta']
                },
                "recent": {
                    "min": r_data['min'],
                    "pts": r_data['pts'],
                    "reb": r_data['reb'],
                    "ast": r_data['ast'],
                    "stl": r_data['stl'],
                    "blk": r_data['blk'],
                    "tov": r_data['tov'],
                    "3pm": r_data['fg3m'],
                    "fgm": r_data['fgm'],
                    "fga": r_data['fga'],
                    "ftm": r_data['ftm'],
                    "fta": r_data['fta']
                }
            })

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(merged, f, indent=2)
            
        print(f"Successfully saved merged stats for {len(merged)} NBA players to {OUTPUT_FILE}")
        return True

    except Exception as e:
        print(f"NBA Player API workflow failed: {e}")
        return False

if __name__ == "__main__":
    fetch_nba_player_stats()

