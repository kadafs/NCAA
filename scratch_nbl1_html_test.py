import requests, re

url = 'https://nbl1.com.au/fixtures'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

try:
    res = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {res.status_code}")
    print(f"Content Length: {len(res.text)}")
    
    # Extract fixture IDs (e.g. 24fed80e-d942-11f0-ae40-a990d4889692)
    fixture_ids = set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', res.text.lower()))
    
    print(f"Extracted {len(fixture_ids)} unique UUIDs")
    
    # Let's test a few to see if they are valid Sportradar fixture IDs
    valid_count = 0
    test_ids = list(fixture_ids)[:10]
    print("\nTesting 10 UUIDs against Sportradar API:")
    for fid in test_ids:
        sr_url = f'https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={fid}'
        sr_res = requests.get(sr_url, timeout=5)
        if sr_res.status_code == 200:
            data = sr_res.json().get('data', {})
            comp = data.get('banner', {}).get('competition', {}).get('name', 'Unknown')
            date = data.get('banner', {}).get('fixture', {}).get('startDate', 'Unknown')
            print(f"  [VALID] {fid} -> {comp} on {date[:10]}")
            valid_count += 1
        else:
            print(f"  [INVALID] {fid}")
            
    print(f"\nSummary: {valid_count} of 10 UUIDs were valid Sportradar fixtures.")
    
except Exception as e:
    print(f"Error: {e}")
