import os
import json
from dotenv import load_dotenv
from supabase import create_client

def dump_keys():
    load_dotenv()
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("ERROR: Missing SUPABASE environment variables.")
        return
        
    supabase = create_client(url, key)
    
    for mode_key in ["nba_safe"]:
        print(f"\n=== LEAGUE: {mode_key} ===")
        try:
            res = supabase.table("predictions_store").select("data").eq("league", mode_key).execute()
            if res.data:
                games = res.data[0]['data']['games']
                for g in games:
                    away_code = g.get('away_details', {}).get('code', 'N/A')
                    home_code = g.get('home_details', {}).get('code', 'N/A')
                    away_name = g.get('away_details', {}).get('name', g.get('away', 'N/A'))
                    home_name = g.get('home_details', {}).get('name', g.get('home', 'N/A'))
                    print(f"[{away_code} vs {home_code}] | Names: {away_name} vs {home_name}")
            else:
                print("No data found.")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    dump_keys()
