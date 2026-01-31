import os
import json
from dotenv import load_dotenv
from supabase import create_client

def check_env():
    load_dotenv()
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("ERROR: Missing SUPABASE environment variables.")
        return
        
    print(f"Connecting to: {url}")
    supabase = create_client(url, key)
    
    for mode in ["ncaa_safe", "ncaa_full"]:
        print(f"\n--- MODE: {mode} ---")
        try:
            res = supabase.table("predictions_store").select("data").eq("league", mode).execute()
            if res.data:
                game = res.data[0]['data']['games'][0]
                print(f"Matchup: {game['matchup']}")
                print(f"Model Total: {game['model_total']}")
                print(f"Trace Length: {len(game['trace'])}")
                print(f"First Trace Line: {game['trace'][0]}")
            else:
                print("No data found for this mode.")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    check_env()
