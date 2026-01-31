import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_db():
    print("--- Checking Audit Summary ---")
    summary = supabase.table("audit_summary").select("*").execute()
    for row in summary.data:
        print(f"League: {row['league']} | Wins: {row['wins']} | Losses: {row['losses']} | Pushes: {row['pushes']} | Win%: {row['win_pct']}%")

    print("\n--- Checking Recent Graded NBA Picks ---")
    nba_picks = supabase.table("predictions_history") \
        .select("*") \
        .eq("league", "nba") \
        .eq("status", "graded") \
        .limit(5) \
        .execute()
    
    if not nba_picks.data:
        print("No graded NBA picks found.")
    for p in nba_picks.data:
        print(f"ID: {p['id']} | Matchup: {p['matchup']} | Date: {p['game_date']} | Win: {p['is_win']}")

    print("\n--- Checking Pending NBA Picks ---")
    nba_pending = supabase.table("predictions_history") \
        .select("*") \
        .eq("league", "nba") \
        .eq("status", "pending") \
        .limit(5) \
        .execute()
    
    if not nba_pending.data:
        print("No pending NBA picks found.")
    for p in nba_pending.data:
        print(f"ID: {p['id']} | Matchup: {p['matchup']} | Date: {p['game_date']}")

if __name__ == "__main__":
    check_db()
