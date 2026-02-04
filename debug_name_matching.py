# debug_name_matching.py
from utils.mapping import clean_team_name, BASKETBALL_ALIASES

def test_match(away, home, odds_key):
    c_away = clean_team_name(away)
    c_home = clean_team_name(home)
    k_low = clean_team_name(odds_key)
    
    a_away = BASKETBALL_ALIASES.get(c_away, c_away)
    a_home = BASKETBALL_ALIASES.get(c_home, c_home)
    reverse_away = [k for k, v in BASKETBALL_ALIASES.items() if v == c_away]
    reverse_home = [k for k, v in BASKETBALL_ALIASES.items() if v == c_home]
    
    away_match = (c_away in k_low or a_away in k_low or any(r in k_low for r in reverse_away))
    home_match = (c_home in k_low or a_home in k_low or any(r in k_low for r in reverse_home))
    
    result = away_match and home_match

    print(f"\nMatch Attempt: [{away}] @ [{home}] in '{odds_key}'")
    print(f"  Clean Names: awy='{c_away}', hme='{c_home}', key='{k_low}'")
    print(f"  Result: {'SUCCESS' if result else 'FAILED'}")

print("--- Isolating Failures ---")

# Ole Miss failure check
test_match("Mississippi", "Marshall", "Ole Miss vs Marshall")

# Middle Tenn failure check
test_match("FIU", "Middle Tennessee", "FIU vs Middle Tenn")

# St. Mary's failure check
test_match("San Diego", "Saint Mary's", "San Diego vs St. Mary's")

# Lehigh vs Maryland (Md) check
test_match("Lehigh", "Maryland", "Lehigh @ Md")
