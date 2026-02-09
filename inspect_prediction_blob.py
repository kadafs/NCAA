import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def inspect_blob(league_key):
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    if not url or not key:
        print("Missing Supabase credentials")
        return
        
    s = create_client(url, key)
    res = s.table('predictions_store').select('data').eq('league', league_key).execute()
    
    if not res.data:
        print(f"No data found for {league_key}")
        return
        
    data = res.data[0]['data']
    print(f"--- Data for {league_key} ---")
    print(f"Timestamp: {data.get('timestamp')}")
    print(f"Mode: {data.get('mode')}")
    print(f"Games Count: {len(data.get('games', []))}")
    
    targets = ["Alabama A&M", "Grambling", "Prairie View", "Florida A&M", "Xavier", "St. John's", "Chicago St."]
    
    for g in data.get('games', []):
        matchup = g.get('matchup', '')
        print(f"- {matchup} | Market: {g.get('market_total')} | Source: {g.get('market_source')}")

if __name__ == "__main__":
    inspect_blob("ncaa_safe")
    print("\n")
    inspect_blob("ncaa")
