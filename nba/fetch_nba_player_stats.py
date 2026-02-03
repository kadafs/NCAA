import json
import os
import time
from nba_api.stats.endpoints import fantasywidget
import sys
# Root addition for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.nba_api_client import RobustNBAClient

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "nba_player_stats.json")

def fetch_nba_player_stats():
    print("Fetching NBA Player Stats (for props) from official API...")
    
    try:
        # Try today's players first (with retries via RobustNBAClient)
        try:
            data = RobustNBAClient.call_endpoint(
                fantasywidget.FantasyWidget,
                todays_players='Y',
                timeout=15
            )
            rows = data['resultSets'][0]['rowSet']
        except Exception as e:
            print(f"Today's active roster fetch failed: {e}. Falling back to all player averages...")
            rows = []

        if not rows:
            print("Primary active roster fetch returned 0 rows. Attempting fallback to all season averages...")
            data = RobustNBAClient.call_endpoint(
                fantasywidget.FantasyWidget,
                todays_players='N',
                timeout=20
            )
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
        print(f"NBA Player API failed after retries: {e}")
        return False

if __name__ == "__main__":
    fetch_nba_player_stats()
