import requests
import json
import sys

# Configuration
API_URL = "https://ncaa-teal.vercel.app/api/predictions?league=ncaa&mode=safe"

def find_clamped_games():
    print(f"Fetching predictions from {API_URL}...")
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = data.get("games", [])
        if not games:
            print("No games found in response.")
            return

        print(f"Analyzing {len(games)} games for outlier clamping...")
        print("-" * 60)
        
        clamped_count = 0
        for game in games:
            raw_total = game.get("rawModelTotal")
            final_total = game.get("modelTotal")
            market_total = game.get("marketTotal")
            
            # Check if raw_total exists and differs from final_total
            if raw_total is not None and final_total is not None:
                # Use a small epsilon for float comparison
                if abs(raw_total - final_total) > 0.01:
                    clamped_count += 1
                    diff = raw_total - final_total
                    direction = "DAMPENED DOWN" if diff > 0 else "BOOSTED UP"
                    
                    print(f"GAME: {game.get('away', {}).get('code')} @ {game.get('home', {}).get('code')}")
                    print(f"  Market: {market_total}")
                    print(f"  Raw Model: {raw_total}")
                    print(f"  Final Model: {final_total}")
                    print(f"  Action: {direction} (shifted by {abs(diff):.2f} points)")
                    print("-" * 60)
        
        if clamped_count == 0:
            print("No clamped games found. The model agrees reasonably well with the market for all games.")
        else:
            print(f"Found {clamped_count} clamped games.")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API.")
        print("Make sure the frontend server is running on port 3001.")
        print("Run: npm run dev (in the frontend directory)")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    find_clamped_games()
