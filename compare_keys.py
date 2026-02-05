import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.data_bridge import UniversalDataBridge
from core.audit_engine import get_canonical_key

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def compare_keys():
    date_str = "2026-02-04"
    print(f"--- Key Comparison for {date_str} ---")
    
    # 1. Scoreboard (Centralized)
    from core.universal_bridge import get_ncaa_scores
    results_map = get_ncaa_scores(date_str)
    print(f"Scoreboard Keys ({len(results_map)}):")
    for k in sorted(results_map.keys())[:10]:
        print(f"  SB: {k}")
    
    # 2. Database Pending
    res = supabase.table("predictions_history") \
        .select("*") \
        .ilike("league", "ncaa") \
        .eq("mode", "full") \
        .eq("game_date", date_str) \
        .eq("status", "pending") \
        .execute()
    
    print(f"\nDB Pending Keys ({len(res.data)}):")
    for row in res.data[:10]:
        parts = [p.strip() for p in row['matchup'].split('@')]
        key = get_canonical_key(parts[0], parts[1])
        print(f"  DB: {key} (Raw: {row['matchup']})")

if __name__ == "__main__":
    compare_keys()
