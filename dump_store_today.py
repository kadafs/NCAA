import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def dump_store():
    print("Fetching today's predictions from predictions_store...")
    res = supabase.table("predictions_store").select("*").ilike("league", "%ncaa%").execute()
    data = res.data
    
    print(f"Total entries for today: {len(data)}")
    
    # Sort by league name
    data.sort(key=lambda x: x['league'])
    
    for row in data:
        print(f"[{row['league']}] Updated: {row['updated_at']}")
        games = row['data'].get('games', [])
        for g in games:
            print(f"  - {g['matchup']} | Market: {g['market_total']} | Source: {g.get('market_source', 'N/A')}")

if __name__ == "__main__":
    dump_store()
