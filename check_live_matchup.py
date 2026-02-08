import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_matchup_in_store(matchup_name):
    print(f"Searching for '{matchup_name}' in predictions_store...")
    res = supabase.table("predictions_store").select("*").execute()
    data = res.data
    
    found = False
    for row in data:
        league = row['league']
        blob = row['data']
        games = blob.get('games', [])
        for g in games:
            if matchup_name.lower() in g['matchup'].lower():
                print(f"MATCH FOUND in [{league}]:")
                print(f" Matchup: {g['matchup']}")
                print(f" Market: {g['market_total']}")
                print(f" Predict: {g['model_total']}")
                print(f" Entry Date (blob): {blob.get('timestamp')}")
                print(f" Updated At (store): {row['updated_at']}")
                found = True
    
    if not found:
        print("Matchup not found in live store.")

if __name__ == "__main__":
    check_matchup_in_store("Loyola Chicago")
