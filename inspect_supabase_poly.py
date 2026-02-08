import os
from dotenv import load_dotenv
from supabase import create_client
import json

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# Fetch NBA Full predictions
response = supabase.table("predictions").select("*").eq("id", "nba_full").execute()

if response.data:
    data = response.data[0]
    predictions = data.get("predictions", [])
    
    print(f"Total predictions: {len(predictions)}")
    
    if predictions:
        first = predictions[0]
        print(f"\nFirst prediction keys: {list(first.keys())}")
        print(f"\nHas 'polymarket' field: {'polymarket' in first}")
        
        if 'polymarket' in first:
            print(f"Polymarket value: {first['polymarket']}")
        
        # Check a few games
        for i, pred in enumerate(predictions[:3]):
            team = pred.get('team', 'Unknown')
            opponent = pred.get('opponent', 'Unknown')
            poly = pred.get('polymarket')
            print(f"\nGame {i+1}: {team} vs {opponent}")
            print(f"  Polymarket: {poly}")
else:
    print("No data found")
