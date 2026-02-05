import requests
import os
import sys

# Add parent dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.audit_engine import get_canonical_key

def dump_sb_keys():
    date_str = "2026-02-04"
    year, month, day = map(int, date_str.split("-"))
    url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    resp = requests.get(url, headers=headers)
    data = resp.json()
    
    print(f"--- All SB Keys for {date_str} ---")
    keys = []
    for g_wrapper in data.get('games', []):
        g = g_wrapper.get('game')
        if not g: continue
        away = g.get('away', {}).get('names', {}).get('short', '')
        home = g.get('home', {}).get('names', {}).get('short', '')
        if away and home:
            key = get_canonical_key(away, home)
            keys.append(f"{key} (Raw: {away} @ {home})")
    
    for k in sorted(keys):
        print(k)

if __name__ == "__main__":
    dump_sb_keys()
