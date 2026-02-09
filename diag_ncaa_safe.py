import os
import sys
from datetime import datetime
import zoneinfo
import json

# Add root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from core.universal_bridge import get_universal_predictions

def diag():
    target_date = datetime(2026, 2, 9, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
    print(f"Diag for NCAA Safe on {target_date.isoformat()}...")
    
    res = get_universal_predictions("ncaa", "safe", date_obj=target_date)
    print(f"Safe Games Found: {len(res.get('games', []))}")
    if len(res.get('games', [])) == 0:
        print("Result:", res)

    res_full = get_universal_predictions("ncaa", "full", date_obj=target_date)
    print(f"Full Games Found: {len(res_full.get('games', []))}")

if __name__ == "__main__":
    diag()
