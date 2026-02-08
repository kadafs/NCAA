import asyncio
import sys
import os
from datetime import datetime, timedelta
import zoneinfo

# Add root for core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.supabase_pusher import push_league_predictions

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

async def backfill():
    # Backfill Feb 4 and 5
    for day in [4, 5]:
        target_date = datetime(2026, 2, day, tzinfo=ET_TZ)
        print(f"Backfilling predictions for: {target_date.strftime('%Y-%m-%d')}")
        
        for league in ["nba", "ncaa"]:
            try:
                await push_league_predictions(league, date_override=target_date)
            except Exception as e:
                print(f"Failed to backfill {league} for {target_date}: {e}")

if __name__ == "__main__":
    asyncio.run(backfill())
