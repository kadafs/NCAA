import requests, re, scrape_nbl1

res = requests.get('https://nbl1.com.au/fixtures', headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
raw_uuids = list(set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', res.text.lower())))

print(f"Found {len(raw_uuids)} UUIDs in HTML.")
valid = 0
for fid in raw_uuids:
    box = scrape_nbl1.extract_box_score(fid)
    if box:
        print(f"[+] VALID FIXTURE: {box['competition']} - {box['home_team']} vs {box['away_team']} ({box['date']})")
        valid += 1
        
print(f"\nTotal Valid Fixtures Found: {valid}")
