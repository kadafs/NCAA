import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_incorrect_backfill():
    print("--- Cleaning Incorrect FULL Mode Records (2026-02-05) ---")
    
    # Check count first
    res = supabase.table("predictions_history") \
        .select("*", count="exact") \
        .eq("mode", "full") \
        .eq("game_date", "2026-02-05") \
        .execute()
        
    print(f"Found {res.count} incorrect records to delete.")
    
    del_res = supabase.table("predictions_history") \
        .delete() \
        .eq("mode", "full") \
        .eq("game_date", "2026-02-05") \
        .execute()
        
    print(f"Deleted rows. {len(del_res.data) if del_res.data else 0} entries removed.")

if __name__ == "__main__":
    clean_incorrect_backfill()
