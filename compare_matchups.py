import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def compare_matchups():
    date_str = "2026-02-04"
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
    from core.audit_engine import get_canonical_key
    
    def get_matchup_key(m):
        parts = [p.strip() for p in m.split('@')]
        if len(parts) != 2: return m
        return get_canonical_key(parts[0], parts[1])

    # Fetch Safe
    res_safe = supabase.table("predictions_history").select("matchup").ilike("league", "ncaa").eq("mode", "safe").eq("game_date", date_str).execute()
    safe_keys = {get_matchup_key(r['matchup']): r['matchup'] for r in res_safe.data}
    
    # Fetch Full
    res_full = supabase.table("predictions_history").select("matchup").ilike("league", "ncaa").eq("mode", "full").eq("game_date", date_str).execute()
    full_keys = {get_matchup_key(r['matchup']): r['matchup'] for r in res_full.data}
    
    print(f"SAFE Unique Keys: {len(safe_keys)}")
    print(f"FULL Unique Keys: {len(full_keys)}")
    
    only_safe_keys = set(safe_keys.keys()) - set(full_keys.keys())
    only_full_keys = set(full_keys.keys()) - set(safe_keys.keys())
    
    if only_safe_keys:
        print("\n--- Keys ONLY in SAFE ---")
        for k in sorted(list(only_safe_keys)):
            print(f"  {k} (Raw: {safe_keys[k]})")
            
    if only_full_keys:
        print("\n--- Keys ONLY in FULL ---")
        for k in sorted(list(only_full_keys)):
            print(f"  {k} (Raw: {full_keys[k]})")

if __name__ == "__main__":
    compare_matchups()
