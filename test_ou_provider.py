from utils.polymarket_provider import PolymarketProvider

provider = PolymarketProvider()
markets = provider.get_markets("nba")

print(f"Total markets found: {len(markets)}")

if markets:
    # Show first market
    first_key = list(markets.keys())[0]
    first_market = markets[first_key]
    
    print(f"\nFirst market key: {first_key}")
    print(f"Title: {first_market.get('title')}")
    print(f"Total: {first_market.get('total')}")
    print(f"Outcomes: {first_market.get('outcomes')}")
    print(f"Prices: {first_market.get('prices')}")
    print(f"URL: {first_market.get('url')}")
    
    # Count how many have totals
    with_totals = sum(1 for m in markets.values() if m.get('total'))
    print(f"\nMarkets with totals: {with_totals}/{len(markets)}")
