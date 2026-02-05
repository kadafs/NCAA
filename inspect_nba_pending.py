import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def inspect_nba_pending():
    print("--- Inspecting Pending NBA Predictions ---")
    res = supabase.table("predictions_history") \
        .select("*") \
        .eq("league", "nba") \
        .eq("status", "pending") \
        .limit(10) \
        .execute()
        
    if not res.data:
        print("No pending NBA games found.")
        return

    for row in res.data:
        print(f"ID: {row['id']} | Date: {row['game_date']} | Created: {row['created_at']} | Matchup: {row['matchup']}")

if __name__ == "__main__":
    inspect_nba_pending()
