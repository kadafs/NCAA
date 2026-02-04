# check_stats.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check():
    print("--- Fetching Audit Summary ---")
    summary = supabase.table("audit_summary").select("*").execute()
    for row in summary.data:
        print(f"League: {row['league']}")
        print(f"  Win %: {row['win_pct']}%")
        print(f"  Record: {row['wins']}W - {row['losses']}L - {row['pushes']}P")
        print(f"  Profit: {row['profit']}")
        print(f"  ROI: {row['roi']}%")
        print("-" * 20)

    print("\n--- Fetching Recent Prediction History Sample ---")
    history = supabase.table("predictions_history").select("*").limit(5).execute()
    for row in history.data:
        print(f"{row['game_date']} | {row['league']} | {row['matchup']} | Status: {row['status']} | Win: {row['is_win']}")

if __name__ == "__main__":
    check()
