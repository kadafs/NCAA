# Universal Supabase Pusher v1.0
import os
import json
import asyncio
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent directory for core imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.universal_bridge import get_universal_predictions

# Load local .env for testing
load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

LEAGUES = ["nba", "ncaa", "euro", "eurocup", "nbl", "acb"]

async def push_league_predictions(league, mode="safe"):
    print(f"Generating predictions for {league.upper()} ({mode})...")
    try:
        # Get standardized JSON from bridge
        data = get_universal_predictions(league, mode)
        
        if "error" in data:
            print(f"Error generating predictions for {league}: {data['error']}")
            return

        # Upsert into Supabase
        # Table schema: league (pk), data (jsonb), updated_at (timestamptz)
        result = supabase.table("predictions_store").upsert({
            "league": league,
            "data": data,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="league").execute()
        
        print(f"Successfully pushed {league.upper()} predictions to Supabase.")
    except Exception as e:
        print(f"Failed to push {league} predictions: {e}")

async def main():
    print("Starting Universal Supabase Push...")
    tasks = [push_league_predictions(league) for league in LEAGUES]
    await asyncio.gather(*tasks)
    print("Push Complete.")

if __name__ == "__main__":
    asyncio.run(main())
