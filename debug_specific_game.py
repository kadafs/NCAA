import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def inspect_game():
    print("Fetching Iowa @ Washington...")
    # Using ilike to match loosely
    res = supabase.table("predictions_history") \
        .select("*") \
        .ilike("matchup", "%Iowa%Washington%") \
        .execute()
    
    if res.data:
        print(json.dumps(res.data, indent=2))
    else:
        print("No matching game found.")

if __name__ == "__main__":
    inspect_game()
