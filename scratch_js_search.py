import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
res = requests.get('https://nbl1.com.au/fixtures', headers=headers, timeout=20)
html = res.text

# Extract all script blocks
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Found {len(scripts)} script blocks")

# Search for API endpoint references
for i, script in enumerate(scripts):
    if not script.strip():
        continue
    keywords = ['services.nbl1', 'fixture', 'fixtureId', 'externalMatch', 
                'sportradar', '/games/', 'api_cache', 'fetch(', 'XMLHttpRequest']
    hits = [(kw, script.find(kw)) for kw in keywords if kw.lower() in script.lower()]
    if hits:
        print(f"\n[Script #{i}] Hits: {[h[0] for h in hits]}")
        print(f"  Length: {len(script)}")
        # Print a snippet around the first hit
        for kw, pos in hits[:2]:
            snippet = script[max(0,pos-100):pos+200]
            print(f"  Context for '{kw}':")
            print(f"  ...{snippet}...")
            print()
