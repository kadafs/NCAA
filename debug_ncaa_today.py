import asyncio
import os
import sys
from datetime import datetime
import zoneinfo

# Add root for core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ncaa.v1_2.populate import fetch_matchups, get_daily_input_sheet
from core.universal_bridge import get_universal_predictions

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

def debug_ncaa_population():
    target_date = datetime.now(ET_TZ)
    print(f"--- Debugging NCAA Population for {target_date.strftime('%Y-%m-%d')} ---")
    
    matchups = fetch_matchups(target_date)
    print(f"Scoreboard fetch found {len(matchups)} games.")
    
    for m in matchups:
        print(f" Matchup: {m['away']} @ {m['home']} | Scoreboard Total: {m.get('total')}")
        
    sheet = get_daily_input_sheet(target_date)
    print(f"\nStandardized sheet contains {len(sheet)} games.")
    
    for s in sheet:
        print(f" Team: {s['team']} vs {s['opponent']} | Market: {s['market_total']} | Source: {s.get('market_source')}")

if __name__ == "__main__":
    debug_ncaa_population()
