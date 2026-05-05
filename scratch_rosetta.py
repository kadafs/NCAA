import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
res = requests.get('https://nbl1.com.au/fixtures', headers=headers, timeout=20)
html = res.text

# Get all script blocks
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

# Print full content of script #7
print("=== Script #7 (full) ===")
print(scripts[7])

# Also find script tags with rosetta-js or similar
print("\n=== Script tags with 'rosetta' in src ===")
script_tags = re.findall(r'<script[^>]+src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
for src in script_tags:
    if 'rosetta' in src.lower():
        print(f"  {src}")

# Also find all external script URLs
print("\n=== All external script src URLs ===")
for src in script_tags:
    print(f"  {src}")
