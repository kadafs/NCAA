import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_mode_distribution():
    print("--- Checking Prediction Modes ---")
    
    # Check 'safe'
    res_safe = supabase.table("predictions_history").select("*", count="exact").eq("mode", "safe").execute()
    print(f"SAFE records: {res_safe.count}")
    
    # Check 'full'
    res_full = supabase.table("predictions_history").select("*", count="exact").eq("mode", "full").execute()
    print(f"FULL records: {res_full.count}")
    
    # Check null (legacy that didn't get default?)
    # Note: select('*') with filter might not catch everything if we don't query explicitly
    # But checking for null mode just in case
    # API doesn't support "is null" easily in py client usually without a specific filter method or query
    # We'll just rely on the above for now.

if __name__ == "__main__":
    check_mode_distribution()
