from utils.polymarket_provider import PolymarketProvider

provider = PolymarketProvider()
markets = provider.get_markets("ncaa")

print(f"NCAA markets found: {len(markets)}")

if markets:
    # Show first few markets
    for i, (key, market) in enumerate(list(markets.items())[:5]):
        print(f"\n{i+1}. Key: {key}")
        print(f"   Title: {market.get('title')}")
        print(f"   Total: {market.get('total')}")
        print(f"   Outcomes: {market.get('outcomes')}")
else:
    print("No NCAA markets found")
