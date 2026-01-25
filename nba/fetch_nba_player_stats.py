import json
import os
from nba_api.stats.endpoints import fantasywidget

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "nba_player_stats.json")

def fetch_nba_player_stats():
    print("Fetching NBA Player Stats (for props) from official API...")
    
    custom_headers = {
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
    
    try:
        # Try today's players first
        widget = fantasywidget.FantasyWidget(todays_players='Y', headers=custom_headers, timeout=30)
        data = widget.get_dict()
        rows = data['resultSets'][0]['rowSet']
        
        if not rows:
            print("Today's players not available yet. Fetching all active player averages instead...")
            widget = fantasywidget.FantasyWidget(todays_players='N', headers=custom_headers, timeout=30)
            data = widget.get_dict()
            rows = data['resultSets'][0]['rowSet']
        
        headers = data['resultSets'][0]['headers']
        
        player_stats = []
        for row in rows:
            p_dict = dict(zip(headers, row))
            
            # Derive FGM/FTM if missing (often missing in FantasyWidget)
            fga = p_dict.get('FGA', 0)
            fg_pct = p_dict.get('FG_PCT', 0)
            fgm = p_dict.get('FGM', fga * fg_pct)
            
            fta = p_dict.get('FTA', 0)
            ft_pct = p_dict.get('FT_PCT', 0)
            ftm = p_dict.get('FTM', fta * ft_pct)

            player_stats.append({
                "id": p_dict['PLAYER_ID'],
                "name": p_dict['PLAYER_NAME'],
                "team": p_dict['TEAM_ABBREVIATION'],
                "pos": p_dict['PLAYER_POSITION'],
                "gp": p_dict['GP'],
                "min": p_dict['MIN'],
                "pts": p_dict['PTS'],
                "reb": p_dict['REB'],
                "ast": p_dict['AST'],
                "stl": p_dict['STL'],
                "blk": p_dict['BLK'],
                "tov": p_dict['TOV'],
                "threes": p_dict['FG3M'],
                "fgm": fgm,
                "fga": fga,
                "ftm": ftm,
                "fta": fta
            })

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(player_stats, f, indent=2)
            
        print(f"Successfully saved stats for {len(player_stats)} active NBA players to {OUTPUT_FILE}")
        return True

    except Exception as e:
        print(f"Error fetching NBA player stats: {e}")
        return False

if __name__ == "__main__":
    fetch_nba_player_stats()
