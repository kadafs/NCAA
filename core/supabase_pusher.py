# Universal Supabase Pusher v1.0
import os
import json
import asyncio
import time
from datetime import datetime
from supabase import create_client, Client, ClientOptions
from dotenv import load_dotenv
import postgrest

# Add parent directory for core imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.universal_bridge import get_universal_predictions

# Load local .env for testing
load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# Increase timeout for large blobs
opts = ClientOptions(postgrest_client_timeout=120)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

async def push_with_retry(table_name, data, league_mode, is_upsert=True, max_retries=3):
    """Generic push with retry logic for Supabase"""
    for attempt in range(max_retries):
        try:
            if is_upsert:
                # Handle both list (history) and dict (store)
                if isinstance(data, list):
                    # For history, we already chunk it before calling this if it's large
                    supabase.table(table_name).upsert(data, on_conflict="id").execute()
                else:
                    supabase.table(table_name).upsert(data, on_conflict="league").execute()
            return True
        except Exception as e:
            wait_time = (attempt + 1) * 2
            print(f"[{league_mode}] Push attempt {attempt+1} failed for {table_name}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"Final failure for {table_name} after {max_retries} attempts.")
                raise e
    return False

LEAGUES = ["nba", "ncaa"]

async def push_league_predictions(league, date_override=None):
    for mode in ["safe", "full"]:
        print(f"Generating predictions for {league.upper()} ({mode})...")
        try:
            # Get standardized JSON from bridge
            data = get_universal_predictions(league, mode, date_obj=date_override)
            
            # Override timestamp if provided
            if date_override:
                data['timestamp'] = date_override.replace(microsecond=0).isoformat()

            
            if "error" in data:
                print(f"Error generating predictions for {league} ({mode}): {data['error']}")
                continue

            if not data.get("games"):
                print(f"No games found for {league.upper()} ({mode}) today. Skipping push.")
                continue

            # 1. Update Live Store (The blob used by the dashboard)
            store_key = f"{league}_{mode}"
            
            # PROTECTIVE GATE: Only update live store if this is a real-time run (no date_override)
            if not date_override:
                
                # DEBUG: Sample first game
                if data.get("games"):
                    first_g = data["games"][0]
                    print(f"DEBUG [{store_key}]: first game total={first_g['model_total']}, trace_len={len(first_g['trace'])}")
    
                store_payload = {
                    "league": store_key,
                    "data": data,
                    "updated_at": datetime.now().isoformat()
                }
                await push_with_retry("predictions_store", store_payload, store_key)
                print(f"Pushed {league} ({mode}) to live store.")
    
                # Backward compatibility: Push 'safe' to the base key as well
                if mode == "safe":
                    base_payload = {
                        "league": league,
                        "data": data,
                        "updated_at": datetime.now().isoformat()
                    }
                    await push_with_retry("predictions_store", base_payload, league)
                    print(f"Updated base {league} key for backward compatibility.")
            else:
                print(f"Skipping live store update for {league} ({mode}) due to date_override.")

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
                # Use chunking to avoid timeouts on large history sets
                chunks = list(chunk_list(history_rows, 50))
                print(f"Archiving {len(history_rows)} games into history ({mode}) in {len(chunks)} chunks...")
                for i, chunk in enumerate(chunks):
                    await push_with_retry("predictions_history", chunk, f"{store_key}_hist_{i}")
                    if len(chunks) > 1:
                        await asyncio.sleep(0.5) # Small cooldown between chunks
                print(f"Completed history archive for {league} ({mode}).")
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
        await push_league_predictions(league) # Default date for CLI run without override mechanism here yet
    print("Push Complete.")

if __name__ == "__main__":
    asyncio.run(main())
