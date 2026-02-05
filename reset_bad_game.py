import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def reset_game():
    game_id = "ncaa_2026-02-04_iowa_washington"
    print(f"Resetting game {game_id} to pending...")
    
    # Update to clear the erroneous score and set back to pending
    # Note: We can't easily 'unset' numeric fields to NULL if the table doesn't allow it, 
    # but we can set them to 0 (which is what they were) or leaves them. 
    # But importantly, set status='pending'.
    
    data = {
        "status": "pending",
        "is_win": None,
        "actual_score_away": None,
        "actual_score_home": None,
        "actual_total": None,
        "profit": None
    }
    
    res = supabase.table("predictions_history").update(data).eq("id", game_id).execute()
    print(f"Update result: {res}")

if __name__ == "__main__":
    reset_game()
