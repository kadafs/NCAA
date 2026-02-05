import os
import sys
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.audit_engine import get_canonical_key

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def compare_keys():
    date_str = "2026-02-04"
    print(f"--- Key Comparison for {date_str} ---")
    
    # 1. Fetch scores like audit_ncaa
    year, month, day = map(int, date_str.split("-"))
    url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    
    resp = requests.get(url, headers=headers, timeout=20)
    data = resp.json()
    results_keys = set()
    for g_wrapper in data.get('games', []):
        g = g_wrapper.get('game')
        if not g: continue
        if "final" in g.get('gameState', '').lower():
            away_name = g.get('away', {}).get('names', {}).get('short', '')
            home_name = g.get('home', {}).get('names', {}).get('short', '')
            if away_name and home_name:
                results_keys.add(get_canonical_key(away_name, home_name))
    
    print(f"Scoreboard Keys ({len(results_keys)}):")
    for k in sorted(list(results_keys))[:10]:
        print(f"  SB: {k}")
    
    # 2. Database Pending
    res = supabase.table("predictions_history") \
        .select("*") \
        .ilike("league", "ncaa") \
        .eq("mode", "full") \
        .eq("game_date", date_str) \
        .eq("status", "pending") \
        .execute()
    
    print(f"\nDB Pending Keys ({len(res.data)}):")
    for row in res.data[:10]:
        parts = [p.strip() for p in row['matchup'].split('@')]
        key = get_canonical_key(parts[0], parts[1])
        matched = "MATCHED" if key in results_keys else "MISSING"
        # Try fuzzy
        if matched == "MISSING":
            for rk in results_keys:
                ra, rh = rk.split('_')
                da, dh = key.split('_')
                if (da in ra or ra in da) and (dh in rh or rh in dh):
                    matched = f"FUZZY:{rk}"
                    break
        print(f"  DB: {key:30} | {matched} | Raw: {row['matchup']}")

if __name__ == "__main__":
    compare_keys()
