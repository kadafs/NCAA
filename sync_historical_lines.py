import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from core.audit_engine import get_canonical_key

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_lines():
    date_str = "2026-02-04"
    print(f"Syncing NCAA lines for {date_str}...")
    
    # 1. Fetch SAFE records
    safe_res = supabase.table("predictions_history")\
        .select("matchup, market_total")\
        .ilike("league", "ncaa")\
        .eq("mode", "safe")\
        .eq("game_date", date_str)\
        .execute()
    
    line_map = {}
    for r in safe_res.data:
        m = r['matchup']
        parts = [p.strip() for p in m.split('@')]
        if len(parts) == 2:
            key = get_canonical_key(parts[0], parts[1])
            line_map[key] = r['market_total']
            
    print(f"Collected {len(line_map)} unique lines from SAFE mode.")
    
    # 2. Fetch FULL records
    full_res = supabase.table("predictions_history")\
        .select("id, matchup, market_total")\
        .ilike("league", "ncaa")\
        .eq("mode", "full")\
        .eq("game_date", date_str)\
        .execute()
    
    updates = []
    skipped = 0
    for r in full_res.data:
        m = r['matchup']
        parts = [p.strip() for p in m.split('@')]
        if len(parts) == 2:
            key = get_canonical_key(parts[0], parts[1])
            if key in line_map:
                new_line = line_map[key]
                if r['market_total'] != new_line:
                    updates.append({
                        "id": r['id'], 
                        "market_total": new_line,
                        "league": "ncaa",
                        "game_date": date_str,
                        "matchup": m,
                        "mode": "full"
                    })
            else:
                skipped += 1
                
    print(f"Found {len(updates)} records needing line updates. {skipped} records missing matching SAFE line.")
    
    # 3. Apply updates
    if updates:
        for i in range(0, len(updates), 50):
            batch = updates[i:i+50]
            supabase.table("predictions_history").upsert(batch, on_conflict="id").execute()
        print(f"Successfully updated {len(updates)} FULL mode lines.")
    else:
        print("No updates needed.")

if __name__ == "__main__":
    sync_lines()
