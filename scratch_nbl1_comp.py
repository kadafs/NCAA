import requests, json

# Get the seasonId from a known fixture
url = 'https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId=6b42622c-d3dd-11f0-b14a-8124d1b57aca'
res = requests.get(url, timeout=10)
data = res.json().get('data', {})
season_id = data.get('seasonId')
comp_id = data.get('banner', {}).get('competition', {}).get('id')
print(f'Season ID: {season_id}')
print(f'Competition ID: {comp_id}')

# Try different Sportradar season/round endpoints
base = 'https://embed-api.eui.connect.sportradar.com/v1/embed/3'
endpoints = [
    f'{base}/season_fixtures?seasonId={season_id}',
    f'{base}/season_fixtures?competitionId={comp_id}&seasonId={season_id}',
    f'{base}/competition_stage_fixtures?competitionId={comp_id}',
    f'{base}/season_rounds?seasonId={season_id}',
    f'{base}/stage_fixtures?seasonId={season_id}',
]

for ep in endpoints:
    try:
        r = requests.get(ep, timeout=8)
        print(f'\n{ep[-60:]}')
        print(f'  Status: {r.status_code}, Size: {len(r.text)}')
        if r.status_code == 200:
            d = r.json()
            print(f'  Keys: {list(d.get("data", {}).keys() if isinstance(d.get("data"), dict) else [])[:5]}')
            print(f'  Data type: {type(d.get("data")).__name__}')
            print(f'  Raw (first 200): {str(d)[:200]}')
    except Exception as e:
        print(f'  Error: {e}')
