from ncaa.v1_2.populate import fetch_matchups
from datetime import datetime
import zoneinfo
from utils.mapping import clean_team_name, find_team_in_dict, BASKETBALL_ALIASES
from ncaa.v1_2.populate import load_json, BARTTORVIK_FILE

def debug_matchups():
    date_obj = datetime(2026, 2, 7, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
    matchups = fetch_matchups(date_obj)
    bt_data = load_json(BARTTORVIK_FILE)
    
    print(f"\nAnalyzing {len(matchups)} matchups...")
    
    for m in matchups:
        c_away = clean_team_name(m['away'])
        c_home = clean_team_name(m['home'])
        
        # Check if they resolve to BartTorvik
        tA = find_team_in_dict(m['away'], bt_data, BASKETBALL_ALIASES)
        tH = find_team_in_dict(m['home'], bt_data, BASKETBALL_ALIASES)
        
        if not tA or not tH:
            print(f"[FAILED] Scoreboard: {m['away']} ({c_away}) @ {m['home']} ({c_home})")
            if not tA: print(f"  !! Away Match Failed !!")
            if not tH: print(f"  !! Home Match Failed !!")

if __name__ == "__main__":
    debug_matchups()
