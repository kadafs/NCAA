import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

URL = "https://gamma-api.polymarket.com/events?closed=false&tag_slug=cbb&limit=10&order=volume24hr&ascending=false"

s = requests.Session()

retries = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)
s.mount('https://', HTTPAdapter(max_retries=retries))

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

for attempt in range(3):
    try:
        print(f"Attempt {attempt + 1}...")
        r = s.get(URL, headers=headers, timeout=15)
        data = r.json()
        
        print(f"Success! Found {len(data)} NCAA events")
        
        if data:
            for e in data[:3]:
                title = e.get('title')
                print(f"  - {title}")
                markets = e.get('markets', [])
                print(f"    Markets: {len(markets)}")
        else:
            print("No NCAA events found on Polymarket today")
        break
        
    except Exception as e:
        print(f"Failed: {e}")
        if attempt < 2:
            time.sleep(2)
        else:
            print("\nConclusion: NCAA markets may not be available or API is unstable for CBB tag")
