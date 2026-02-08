import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_graded():
    print("Analyzing graded NCAA records by date...")
    res = supabase.table("predictions_history").select("game_date, mode").ilike("league", "ncaa").eq("status", "graded").execute()
    data = res.data
    
    dist = {} # date -> {mode -> count}
    
    for row in data:
        d = row['game_date']
        m = row['mode']
        if d not in dist: dist[d] = {}
        dist[d][m] = dist[d].get(m, 0) + 1
        
    for d in sorted(dist.keys()):
        counts = dist[d]
        print(f" {d}: SAFE={counts.get('safe', 0)}, FULL={counts.get('full', 0)}")

if __name__ == "__main__":
    analyze_graded()
