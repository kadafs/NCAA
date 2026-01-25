import json
import os
import time
from nba_api.stats.endpoints import leaguedashplayerstats

# Output path
OUTPUT_FILE = "data/nba_player_stats.json"

# Shared headers for NBA API
NBA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
}

def fetch_player_positions():
    """Fetches player positions using FantasyWidget."""
    from nba_api.stats.endpoints import fantasywidget
    print("Fetching Player Positions...")
    try:
        widget = fantasywidget.FantasyWidget(todays_players='N', headers=NBA_HEADERS, timeout=30)
        data = widget.get_dict()
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        pos_map = {}
        for row in rows:
            d = dict(zip(headers, row))
            pos_map[d['PLAYER_ID']] = d.get('PLAYER_POSITION', 'G') # Default to G
        return pos_map
    except Exception as e:
        print(f"Warning: Could not fetch positions ({e}). Using defaults.")
        return {}

def fetch_player_data(last_n=0):
    """Fetches player stats for the current season."""
    print(f"Fetching {'Season' if last_n==0 else f'Last {last_n}'} Player Stats...")
    stats = leaguedashplayerstats.LeagueDashPlayerStats(
        last_n_games=last_n,
        per_mode_detailed='PerGame',
        season='2025-26',
        season_type_all_star='Regular Season',
        headers=NBA_HEADERS,
        timeout=30
    ).get_dict()
    
    headers = stats['resultSets'][0]['headers']
    rows = stats['resultSets'][0]['rowSet']
    
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

def fetch_and_merge_player_stats():
    try:
        # 1. Fetch Season Averages
        season_stats = fetch_player_data(0)
        
        # 2. Fetch Last 5 Games
        recent_stats = fetch_player_data(5)
        
        # 3. Fetch Positions
        pos_map = fetch_player_positions()
        
        # 4. Merge
        merged = []
        for pid, s_data in season_stats.items():
            r_data = recent_stats.get(pid, s_data) # Fallback to season if no recent games
            p_pos = pos_map.get(pid, "G") # Fallback to G
            
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
                    "fg3m": s_data['fg3m'],
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
                    "fg3m": r_data['fg3m'],
                    "fgm": r_data['fgm'],
                    "fga": r_data['fga'],
                    "ftm": r_data['ftm'],
                    "fta": r_data['fta']
                }
            })

        if not os.path.exists('data'):
            os.makedirs('data')

        with open(OUTPUT_FILE, "w") as f:
            json.dump(merged, f, indent=2)
            
        print(f"Successfully saved merged stats for {len(merged)} NBA players to {OUTPUT_FILE}")
        return True

    except Exception as e:
        print(f"Error fetching NBA player stats: {e}")
        return False

if __name__ == "__main__":
    fetch_and_merge_player_stats()
