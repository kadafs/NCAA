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

LEAGUES = ["nba", "ncaa"]

async def push_league_predictions(league):
    for mode in ["safe", "full"]:
        print(f"Generating predictions for {league.upper()} ({mode})...")
        try:
            # Get standardized JSON from bridge
            data = get_universal_predictions(league, mode)
            
            if "error" in data:
                print(f"Error generating predictions for {league} ({mode}): {data['error']}")
                continue

            if not data.get("games"):
                print(f"No games found for {league.upper()} ({mode}) today. Skipping push.")
                continue

            # 1. Update Live Store (The blob used by the dashboard)
            # Use composite key for unique storage
            store_key = f"{league}_{mode}"
            
            # DEBUG: Sample first game
            if data.get("games"):
                first_g = data["games"][0]
                print(f"DEBUG [{store_key}]: first game total={first_g['model_total']}, trace_len={len(first_g['trace'])}")
                if len(first_g['trace']) > 0:
                    print(f"DEBUG [{store_key}]: first trace line='{first_g['trace'][0]}'")

            supabase.table("predictions_store").upsert({
                "league": store_key,
                "data": data,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="league").execute()
            print(f"Pushed {league} ({mode}) to live store.")

            # Backward compatibility: Push 'safe' to the base key as well
            if mode == "safe":
                supabase.table("predictions_store").upsert({
                    "league": league,
                    "data": data,
                    "updated_at": datetime.now().isoformat()
                }, on_conflict="league").execute()
                print(f"Updated base {league} key for backward compatibility.")

            # 2. Update History Archive (Push BOTH modes with unique IDs)
            history_rows = []
            for g in data.get("games", []):
                away = g.get('away_details', {}).get('name') or g.get('away', {}).get('name') or g.get('away_team')
                home = g.get('home_details', {}).get('name') or g.get('home', {}).get('name') or g.get('home_team')
                
                if not away or not home: continue
                
                # Unique ID: nba_2026-01-27_lakers_celtics_full
                game_date = data.get('timestamp', datetime.now().isoformat())[:10]
                base_id = f"{league}_{game_date}_{away}_{home}".replace(" ", "_").lower()
                row_id = f"{base_id}_{mode}" # e.g. ..._safe or ..._full
                
                history_rows.append({
                    "id": row_id,
                    "league": league,
                    "game_date": game_date,
                    "matchup": f"{away} @ {home}",
                    "market_total": float(g.get('market_total', 0)),
                    "model_total": float(g.get('model_total', 0)),
                    "edge": float(g.get('edge', 0)),
                    "status": "pending",
                    "mode": mode,
                    "updated_at": datetime.now().isoformat()
                })

            if history_rows:
                # Use upsert to update existing rows or insert new ones
                supabase.table("predictions_history").upsert(history_rows, on_conflict="id").execute()
                print(f"Archived {len(history_rows)} games into history ({mode}).")
        except Exception as e:
            print(f"Failed to push {league} ({mode}) predictions: {e}")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Universal Supabase Pusher v1.1")
    parser.add_argument("--league", choices=["nba", "ncaa", "all"], default="all", help="League to push (default: all)")
    args = parser.parse_args()

    print(f"Starting Universal Supabase Push (Target: {args.league.upper()})...")
    
    target_leagues = LEAGUES if args.league == "all" else [args.league]

    # Execute sequentially for stability
    for league in target_leagues:
        await push_league_predictions(league)
    print("Push Complete.")

if __name__ == "__main__":
    asyncio.run(main())
