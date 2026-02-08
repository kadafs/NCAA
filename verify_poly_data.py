from core.data_bridge import UniversalDataBridge
import json

def verify():
    print("--- Verifying Polymarket Data Injection via Bridge ---")
    bridge = UniversalDataBridge("nba")
    
    # This triggers the fetch
    feed = bridge.get_standardized_sheet()
    
    poly_count = 0
    
    for game in feed:
        poly = game.get("polymarket")
        if poly:
            poly_count += 1
            print(f"\n[MATCH FOUND] {game['team']} vs {game['opponent']}")
            print(f"Title: {poly.get('title')}")
            # print(f"Prices: {poly.get('prices')}")
            
    print(f"\nTotal Games: {len(feed)}")
    print(f"Polymarket Matches: {poly_count}")
    
    if poly_count == 0:
        print("\nWARNING: No Polymarket data found in Bridge output.")
    else:
        print("\nSUCCESS: Polymarket data is being injected.")

if __name__ == "__main__":
    verify()
