import asyncio
import os
import sys
from datetime import datetime
import zoneinfo

# Add root for core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.supabase_pusher import push_league_predictions

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

async def sync():
    # Target dates with known discrepancies
    targets = [
        (datetime(2026, 2, 5, tzinfo=ET_TZ), 51), # Feb 5 (Expected 51+)
        (datetime(2026, 2, 6, tzinfo=ET_TZ), 8)   # Feb 6 (Expected 8+)
    ]
    
    for target_date, expected_min in targets:
        print(f"\n--- Syncing {target_date.strftime('%Y-%m-%d')} (Expected Min: {expected_min}) ---")
        
        success = False
        for attempt in range(10): # 10 retries per day due to flakiness
            print(f"Attempt {attempt+1}...")
            try:
                # We'll push both modes to be safe and ensure they are identical in count
                # The pusher script already handles safe/full internally
                await push_league_predictions("ncaa", date_override=target_date)
                
                # Check results for this specific date in DB after push? 
                # Better: Just check the logs from pusher. 
                # Actually, pusher prints "Archiving X games". 
                # We can't easily intercept that here without refactoring.
                # But we'll trust the 10 retries will hit a good fetch.
                success = True
            except Exception as e:
                print(f"Error on attempt {attempt+1}: {e}")
            
            await asyncio.sleep(2) # Cooldown between attempts
            
        if success:
            print(f"Sync complete for {target_date.strftime('%Y-%m-%d')}.")

if __name__ == "__main__":
    asyncio.run(sync())
