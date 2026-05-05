import requests, re, scrape_nbl1, json, os

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Try sitemap for game URLs
print("=== Checking NBL1 sitemap ===")
sitemap_urls = [
    'https://www.nbl1.com.au/sitemap.xml',
    'https://nbl1.com.au/sitemap.xml',
    'https://www.nbl1.com.au/sitemap_index.xml',
    'https://www.nbl1.com.au/robots.txt',
]
for url in sitemap_urls:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"  {url.split('/')[-1]}: {r.status_code}, {len(r.text)} bytes")
    if r.status_code == 200 and 'games' in r.text.lower():
        # Extract game URLs
        game_urls = re.findall(r'https?://(?:www\.)?nbl1\.com\.au/games/([0-9a-f-]{36})', r.text)
        print(f"    -> Found {len(game_urls)} game URLs!")
        print(f"    Sample: {game_urls[:3]}")
    elif r.status_code == 200:
        print(f"    Content (first 300): {r.text[:300]}")
