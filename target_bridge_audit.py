import os
import sys
from datetime import datetime
import zoneinfo

# Add root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from core.data_bridge import UniversalDataBridge

def target_audit():
    bridge = UniversalDataBridge("ncaa")
    target_date = datetime(2026, 2, 9, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
    
    print(f"Auditing Data Bridge for {target_date.strftime('%Y-%m-%d')}...")
    sheet = bridge.get_standardized_sheet(date_obj=target_date)
    
    targets = ["Xavier", "St. John's", "Chicago St.", "Saint Francis", "Jackson St.", "Ark.-Pine Bluff", "Northwestern St.", "Lamar University", "Central Ark.", "North Ala."]
    
    print("\n--- ALL RESULTS ---")
    for game in sheet:
        away = game.get('team')
        home = game.get('opponent')
        market = game.get('market_total')
        source = game.get('market_source', 'Unknown')
        print(f"{away} @ {home} -> Market: {market} (Source: {source})")

if __name__ == "__main__":
    target_audit()
