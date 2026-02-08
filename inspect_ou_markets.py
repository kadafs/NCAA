import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://gamma-api.polymarket.com/events?closed=false&tag_slug=nba&limit=10&order=volume24hr&ascending=false"

def test_ou_markets():
    print("\n--- Checking O/U Markets ---")
    s = requests.Session()
    
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    s.mount('https://', HTTPAdapter(max_retries=retries))
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    try:
        r = s.get(URL, headers=headers, timeout=15)
        data = r.json()
        
        print(f"Fetched {len(data)} events.\n")
        
        for e in data[:5]:  # Check first 5 events
            title = e.get('title')
            if " vs" in title.lower():
                print(f"\n=== {title} ===")
                for m in e.get('markets', []):
                    q = m.get('question', '')
                    # Look for O/U markets
                    if 'O/U' in q or 'over/under' in q.lower() or 'total' in q.lower():
                        outcomes = m.get('outcomes', '[]')
                        prices = m.get('outcomePrices', '[]')
                        print(f"  [O/U] Market: {q}")
                        print(f"    Outcomes: {outcomes}")
                        print(f"    Prices: {prices}")
                        
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_ou_markets()
