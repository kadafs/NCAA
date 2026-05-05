import scrape_nbl1, requests, re
res = requests.get('https://nbl1.com.au/fixtures', headers={'User-Agent': 'Mozilla/5.0'})
raw_uuids = list(set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', res.text.lower())))
print('Checking first 20 UUIDs...')
valid_count = 0
for fid in raw_uuids[:20]:
    try:
        box = scrape_nbl1.extract_box_score(fid)
        if box:
            print(f'[+] Valid box score: {box["competition"]} - {box["home_team"]} vs {box["away_team"]}')
            valid_count += 1
        else:
            print(f'[-] Invalid/None for {fid}')
    except Exception as e:
        print(f'[!] Error for {fid}: {e}')
print(f'Valid count: {valid_count}')
