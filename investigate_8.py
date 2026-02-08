import os
import sys
from utils.ssl_adapter import get_robust_session
from utils.odds_provider import extract_total_for_matchup
from utils.mapping import clean_team_name

# Add root for core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def investigate_8():
    url = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa?date=2026-02-07"
    session = get_robust_session(retries=5)
    
    odds_data = session.get(url).json()
    
    targets = [
        ("Nebraska", "Rutgers"),
        ("USC", "Nicholls St."),
        ("Alcorn St.", "Arkansas Pine Bluff"),
        ("Mississippi", "Texas"),
        ("Gardner Webb", "Presbyterian"),
        ("Buffalo", "South Alabama"),
        ("North Alabama", "Austin Peay"),
        ("Incarnate Word", "McNeese St.")
    ]
    
    for away, home in targets:
        total = extract_total_for_matchup(odds_data, away, home)
        print(f"'{away}' @ '{home}' -> {total}")
        if not total:
            # Check substrings manually
            c_away = clean_team_name(away)
            c_home = clean_team_name(home)
            for k in odds_data:
                k_clean = clean_team_name(k)
                match_a = c_away in k_clean
                match_h = c_home in k_clean
                if match_a or match_h:
                    print(f"  Partial match in key '{k}': Away={match_a}, Home={match_h}")

if __name__ == "__main__":
    investigate_8()
