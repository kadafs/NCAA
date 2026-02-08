import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def find_status_mismatch():
    print("Fetching all NCAA records...")
    res = supabase.table("predictions_history").select("*").ilike("league", "ncaa").limit(2000).execute()
    data = res.data
    
    matchups = {}
    for row in data:
        key = (row['game_date'], row['matchup'].lower().strip())
        if key not in matchups: matchups[key] = {}
        matchups[key][row['mode']] = row['status']
        
    mismatch = []
    for key, modes in matchups.items():
        if 'safe' in modes and 'full' in modes:
            if modes['safe'] != modes['full']:
                mismatch.append((key, modes['safe'], modes['full']))
                
    if mismatch:
        print(f"\nFound {len(mismatch)} status mismatches:")
        for key, s_stat, f_stat in mismatch:
            print(f" {key[0]} {key[1]}: SAFE={s_stat}, FULL={f_stat}")
    else:
        print("\nNo status mismatches found.")

if __name__ == "__main__":
    find_status_mismatch()
