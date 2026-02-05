import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def debug_audit():
    print("--- Audit Summary ---")
    res = supabase.table("audit_summary").select("*").execute()
    for row in res.data:
        print(f"League: '{row['league']}' | Record: {row['wins']}-{row['losses']}-{row.get('pushes',0)}")
    
    print("\n--- Detailed NCAA Mode Counts ---")
    res = supabase.table("predictions_history").select("league, mode, status").ilike("league", "ncaa").execute()
    counts = {}
    for r in res.data:
        key = (r['league'], r['mode'], r['status'])
        counts[key] = counts.get(key, 0) + 1
    
    for key, count in counts.items():
        print(f"League: {key[0]} | Mode: {key[1]} | Status: {key[2]} | Count: {count}")

if __name__ == "__main__":
    debug_audit()
