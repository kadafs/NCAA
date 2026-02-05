import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def inspect_full_rows():
    print("--- Inspecting FULL Mode Predictions ---")
    
    res = supabase.table("predictions_history") \
        .select("*") \
        .eq("mode", "full") \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()
        
    if not res.data:
        print("No FULL mode records found.")
        return

    for row in res.data:
        print(f"ID: {row['id']} | Date: {row['game_date']} | Status: {row['status']} | Matchup: {row['matchup']}")

if __name__ == "__main__":
    inspect_full_rows()
