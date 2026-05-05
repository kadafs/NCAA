import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Fetch rosetta.js
print("=== Fetching rosetta.js ===")
r = requests.get('https://nbl1-webflow.s3.ap-southeast-2.amazonaws.com/prod/rosetta.js', headers=headers, timeout=15)
print(f"Status: {r.status_code}, Size: {len(r.text)}")
js = r.text

# Find URLs and API endpoints
urls = re.findall(r'https?://[^\s"\'`<>\)]+', js)
for u in urls[:30]:
    print(f"  URL: {u}")

# Find rosetta domain references
print("\n=== Rosetta domain/API patterns ===")
for kw in ['rosetta', 'fixture', 'season', 'fetch', 'api_cache', 'sportradar', '/v1/', '/v2/']:
    positions = [m.start() for m in re.finditer(kw, js, re.IGNORECASE)]
    if positions:
        pos = positions[0]
        print(f"\n  '{kw}' ({len(positions)} hits). First context:")
        print(f"  ...{js[max(0,pos-80):pos+200]}...")

# Also query rosetta.nbl1.com.au directly
print("\n=== Testing rosetta.nbl1.com.au API directly ===")
test_urls = [
    'https://rosetta.nbl1.com.au/v1/fixtures?year=2026',
    'https://rosetta.nbl1.com.au/fixtures?year=2026',
    'https://rosetta.nbl1.com.au/api/fixtures?year=2026',
    'https://rosetta.nbl1.com.au/v1/season/2026/fixtures',
]
for url in test_urls:
    try:
        r2 = requests.get(url, headers=headers, timeout=8)
        print(f"  {url.split('nbl1.com.au')[-1]}: {r2.status_code}, {len(r2.text)} bytes")
        if r2.status_code == 200:
            print(f"  Preview: {r2.text[:300]}")
    except Exception as e:
        print(f"  {url}: ERROR - {e}")
