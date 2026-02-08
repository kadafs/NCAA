import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add parent directory for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.universal_bridge import get_universal_predictions
import json

# Get predictions
data = get_universal_predictions("nba", "full")

if data.get("games"):
    first_game = data["games"][0]
    print(f"Total games: {len(data['games'])}")
    print(f"\nFirst game: {first_game.get('away')} @ {first_game.get('home')}")
    print(f"Keys in game object: {list(first_game.keys())}")
    print(f"\nHas 'polymarket' field: {'polymarket' in first_game}")
    
    if 'polymarket' in first_game:
        poly = first_game['polymarket']
        print(f"Polymarket value: {poly}")
        if poly:
            print(f"  Title: {poly.get('title')}")
            print(f"  Prices: {poly.get('prices')}")
    else:
        print("ERROR: polymarket field is missing!")
        
    # Check a few more games
    print(f"\n--- Checking all games for polymarket ---")
    for i, game in enumerate(data["games"]):
        poly = game.get('polymarket')
        status = "✓" if poly else "✗"
        print(f"{status} Game {i+1}: {game.get('away')} @ {game.get('home')}")
else:
    print("No games found")
