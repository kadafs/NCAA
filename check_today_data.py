import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import zoneinfo

load_dotenv()

ET_TZ = zoneinfo.ZoneInfo("America/New_York")
date_str = datetime.now(ET_TZ).strftime("%Y-%m-%d")

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_today_counts():
    print(f"--- Checking Game Counts for {date_str} ---")
    res = supabase.table("predictions_history").select("league").eq("game_date", date_str).execute()
    counts = {}
    for row in res.data:
        l = row['league']
        counts[l] = counts.get(l, 0) + 1
    
    for l, count in counts.items():
        print(f"League: {l} | Games Today: {count}")

if __name__ == "__main__":
    check_today_counts()
