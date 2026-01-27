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

        if not data.get("games"):
            print(f"No games found for {league.upper()} today. Skipping Supabase push to preserve existing data.")
            return

        # 1. Update Live Store (The blob used by the dashboard)
        supabase.table("predictions_store").upsert({
            "league": league,
            "data": data,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="league").execute()

        # 2. Update History Archive (Individual games for grading)
        history_rows = []
        for g in data.get("games", []):
            away = g.get('away_details', {}).get('name') or g.get('away', {}).get('name') or g.get('away_team')
            home = g.get('home_details', {}).get('name') or g.get('home', {}).get('name') or g.get('home_team')
            
            if not away or not home: continue
            
            # Unique ID prevents duplicates: nba_2026-01-27_Lakers_Celtics
            game_date = data.get('timestamp', datetime.now().isoformat())[:10]
            row_id = f"{league}_{game_date}_{away}_{home}".replace(" ", "_").lower()
            
            history_rows.append({
                "id": row_id,
                "league": league,
                "game_date": game_date,
                "matchup": f"{away} @ {home}",
                "market_total": float(g.get('market_total', 0)),
                "model_total": float(g.get('model_total', 0)),
                "edge": float(g.get('edge', 0)),
                "status": "pending",
                "updated_at": datetime.now().isoformat()
            })

        if history_rows:
            supabase.table("predictions_history").upsert(history_rows, on_conflict="id").execute()
            print(f"✅ Archived {len(history_rows)} games into history.")
    except Exception as e:
        print(f"Failed to push {league} predictions: {e}")

async def main():
    print("Starting Universal Supabase Push...")
    tasks = [push_league_predictions(league) for league in LEAGUES]
    await asyncio.gather(*tasks)
    print("Push Complete.")

if __name__ == "__main__":
    asyncio.run(main())
