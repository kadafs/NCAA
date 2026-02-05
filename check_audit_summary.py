import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_summary_keys():
    print("--- Audit Summary Keys ---")
    res = supabase.table("audit_summary").select("*").execute()
    for row in res.data:
        print(f"League Key: {row['league']} | Wins: {row['wins']} | Losses: {row['losses']}")

if __name__ == "__main__":
    check_summary_keys()
