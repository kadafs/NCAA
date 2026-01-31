import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def simulate_api():
    # 1. Fetch Summary Data
    summary = supabase.table("audit_summary").select("*").execute()
    
    # 2. Fetch Recent Graded Picks
    recent = supabase.table("predictions_history") \
        .select("*") \
        .eq("status", "graded") \
        .order("game_date", desc=True) \
        .limit(10) \
        .execute()
    
    data = {
        "metrics": summary.data,
        "recent": recent.data
    }
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    simulate_api()
