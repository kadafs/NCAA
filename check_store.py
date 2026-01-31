from supabase import create_client
import os
import json
from dotenv import load_dotenv

def check_store():
    load_dotenv()
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        print("Missing env vars")
        return
        
    s = create_client(url, key)
    
    for mode in ["ncaa_safe", "ncaa_full"]:
        print(f"\n--- Checking {mode} ---")
        res = s.table('predictions_store').select('data').eq('league', mode).execute()
        if res.data:
            games = res.data[0]['data'].get('games', [])
            if games:
                g = games[0]
                print(f"Matchup: {g['matchup']}")
                print(f"Model Total: {g['model_total']}")
                print(f"Trace Lines: {len(g['trace'])}")
                print(f"Trace[0]: {g['trace'][0]}")
            else:
                print("No games in data blob")
        else:
            print("No record found")

if __name__ == "__main__":
    check_store()
