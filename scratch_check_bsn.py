import requests, re, json
url = 'https://nbl1.com.au/games/24fed80e-d942-11f0-ae40-a990d4889692'
res = requests.get(url)
print('Response length:', len(res.text))

# Check for JSON payloads embedded in the HTML (like Next.js __NEXT_DATA__)
next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
if next_data_match:
    print('Found __NEXT_DATA__')
    data = json.loads(next_data_match.group(1))
    print('Keys:', data.keys())
    # Try to find game stats
    try:
        page_props = data.get('props', {}).get('pageProps', {})
        print('pageProps keys:', page_props.keys())
    except:
        pass
else:
    print('No __NEXT_DATA__ found')
