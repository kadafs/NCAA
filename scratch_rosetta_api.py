import requests, re, json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.nbl1.com.au/fixtures',
    'Origin': 'https://www.nbl1.com.au',
}

# Test the Rosetta API endpoint
print("=== Testing prod.rosetta.nbl1.com.au/get ===")
test_urls = [
    'https://prod.rosetta.nbl1.com.au/get',
    'https://prod.rosetta.nbl1.com.au/get?year=2026',
    'https://prod.rosetta.nbl1.com.au/get?collection=fixtures&year=2026',
    'https://prod.rosetta.nbl1.com.au/get?type=fixtures',
    'https://prod.rosetta.nbl1.com.au/get?seasonFixtureYear=2026',
]
for url in test_urls:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"\n  {url.split('nbl1.com.au')[-1]}: {r.status_code}, {len(r.text)} bytes")
        if r.status_code == 200 and len(r.text) > 20:
            print(f"  Preview: {r.text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")

# Also fetch fixturesUtils.js to see what params it passes
print("\n=== Fetching fixturesUtils.js ===")
r2 = requests.get('https://nbl1-webflow.s3.ap-southeast-2.amazonaws.com/prod/fixturesUtils.js', headers=headers, timeout=15)
print(f"Status: {r2.status_code}, Size: {len(r2.text)}")
js2 = r2.text

# Find URL/API patterns
for kw in ['rosettaApi', '/get', 'fetch', 'fixture', 'seasonFixtureYear', 'filter']:
    m = re.search(kw, js2, re.IGNORECASE)
    if m:
        pos = m.start()
        print(f"\n  '{kw}' context:")
        print(f"  ...{js2[max(0,pos-100):pos+250]}...")
