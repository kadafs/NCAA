import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_fields():
    res = supabase.table("predictions_history").select("*").eq("mode", "full").limit(1).execute()
    if res.data:
        r = res.data[0]
        print(f"League: '{r['league']}'")
        print(f"Date: '{r['game_date']}'")
        print(f"Status: '{r['status']}'")
        print(f"ID: '{r['id']}'")
    else:
        print("No full mode data found.")

if __name__ == "__main__":
    check_fields()
