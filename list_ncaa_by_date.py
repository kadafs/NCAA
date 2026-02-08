import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_date(date_str):
    print(f"Listing all NCAA records for {date_str}...")
    res = supabase.table("predictions_history").select("*").ilike("league", "ncaa").eq("game_date", date_str).execute()
    data = res.data
    
    modes = {}
    for row in data:
        m = row['mode']
        modes[m] = modes.get(m, 0) + 1
        
    print(f"Counts: {modes}")
    if data:
        print(f"Sample: {data[0]['matchup']} ({data[0]['mode']}, {data[0]['status']})")

if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "2026-02-05"
    list_date(d)
