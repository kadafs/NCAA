import requests, re
url = 'https://nbl1.com.au/fixtures'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
res = requests.get(url, headers=headers)
print('Length of html:', len(res.text))

# Search for metadata_id or similar in the HTML
metadata_ids = set(re.findall(r'metadata_id["\'=:\s]+(\d+)', res.text))
print('metadata_ids found:', metadata_ids)

# Search for any fixture IDs in the raw HTML
fixture_ids = set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', res.text))
print('fixture_ids found (count):', len(fixture_ids))
print('sample fixture ids:', list(fixture_ids)[:5])
