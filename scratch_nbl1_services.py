import requests, json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://www.nbl1.com.au/',
    'Origin': 'https://www.nbl1.com.au',
}

comp_ids = {
    'NBL1 South Men':    'e1b54948-7b55-11eb-9e56-8205bb8987e9',
    'NBL1 Central Women':'e1bb825e-7b55-11eb-9e56-8205bb8987e9',
    'NBL1 East Men':     'a9909f44-168d-11ec-b50f-1a6efa0e668e',
    'NBL1 North Women':  'e1b77240-7b55-11eb-9e56-8205bb8987e9',
}

base = 'https://prod.services.nbl1.com.au/api_cache/nbl1/sportradar'

# Attempt 1: get all games via content route, no metadata_id filter
routes = [
    f'{base}?format=true&route=schedule&limit=100',
    f'{base}?format=true&limit=100&fields=externalMatchId',
    f'{base}?format=true&route=content&limit=100&fields=externalMatchId',
]

print("=== NBL1 Services API exploration ===\n")
for url in routes:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"URL: ...{url[-60:]}")
        print(f"  Status: {r.status_code}, Size: {len(r.text)}")
        if r.status_code == 200:
            try:
                d = r.json()
                data = d.get('data')
                print(f"  data type: {type(data).__name__}")
                if isinstance(data, list) and data:
                    print(f"  Items: {len(data)}, first keys: {list(data[0].keys())[:6]}")
                    # Check if externalMatchId is present
                    for item in data[:3]:
                        eid = item.get('externalMatchId')
                        if eid:
                            print(f"    externalMatchId: {eid}")
                elif isinstance(data, dict):
                    print(f"  Dict keys: {list(data.keys())[:5]}")
            except Exception as e:
                print(f"  JSON error: {e}")
                print(f"  Raw: {r.text[:200]}")
    except Exception as e:
        print(f"  Request error: {e}")
    print()
