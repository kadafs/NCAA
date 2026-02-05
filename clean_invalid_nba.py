import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_invalid_nba_rows():
    print("--- Cleaning Invalid NBA Predictions for 2026-02-04 ---")
    
    # Verify count first
    res = supabase.table("predictions_history") \
        .select("*") \
        .eq("league", "nba") \
        .eq("game_date", "2026-02-04") \
        .eq("status", "pending") \
        .execute()
        
    print(f"Found {len(res.data)} invalid rows to delete.")
    
    del_res = supabase.table("predictions_history") \
        .delete() \
        .eq("league", "nba") \
        .eq("game_date", "2026-02-04") \
        .eq("status", "pending") \
        .execute()
        
    print(f"Deleted rows. {len(del_res.data) if del_res.data else 0} entries removed.")

if __name__ == "__main__":
    clean_invalid_nba_rows()
