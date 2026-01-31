import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_summary_only():
    print("--- Checking Audit Summary ---")
    summary = supabase.table("audit_summary").select("*").execute()
    if not summary.data:
        print("Audit summary table is empty.")
    for row in summary.data:
        print(f"League: {row['league']} | Wins: {row['wins']} | Losses: {row['losses']} | Pushes: {row['pushes']} | Profit: {row['profit']} | Win%: {row['win_pct']}%")

if __name__ == "__main__":
    check_summary_only()
