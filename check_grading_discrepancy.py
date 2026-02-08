import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_grading_discrepancy():
    print("Fetching all NCAA records...")
    res = supabase.table("predictions_history").select("*").ilike("league", "ncaa").limit(2000).execute()
    data = res.data
    
    # matchup_key -> mode -> status
    matchups = {}
    
    for row in data:
        m_key = (row['game_date'], row['matchup'].lower().strip())
        if m_key not in matchups:
            matchups[m_key] = {}
        matchups[m_key][row['mode']] = row['status']
        
    discrepancies = []
    for m_key, modes in matchups.items():
        if 'safe' in modes and 'full' in modes:
            if modes['safe'] != modes['full']:
                discrepancies.append((m_key, modes['safe'], modes['full']))
        elif 'safe' in modes:
            discrepancies.append((m_key, modes['safe'], "MISSING"))
        elif 'full' in modes:
            discrepancies.append((m_key, "MISSING", modes['full']))
            
    if discrepancies:
        print("\n--- Grading/Presence Discrepancies ---")
        for m_key, safe_status, full_status in discrepancies:
            print(f" {m_key[0]} {m_key[1]}: SAFE={safe_status}, FULL={full_status}")
    else:
        print("\nNo grading or presence discrepancies found.")

if __name__ == "__main__":
    check_grading_discrepancy()
