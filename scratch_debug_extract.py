import requests, json

uid = "9169b7de-d6e8-11f0-9810-259df422383b"
url = f"https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={uid}"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
res = requests.get(url, headers=headers, timeout=15)
data = res.json().get('data', {})

banner = data.get("banner", {})
fixture_meta = banner.get("fixture", {})

print(f"Fixture Meta keys: {list(fixture_meta.keys())}")
print(f"startDate: {fixture_meta.get('startDate')}")
print(f"start: {fixture_meta.get('start')}")

# Try to find date somewhere else
print(f"Banner keys: {list(banner.keys())}")

stats_base = data.get("statistics", {}).get("data", {}).get("base", {})
home_data = stats_base.get("home", {})

print(f"Home Data keys: {list(home_data.keys())}")
persons = home_data.get("persons", [])
if persons:
    print(f"Persons[0] keys: {list(persons[0].keys())}")
    rows = persons[0].get("rows", [])
    if rows:
        print(f"rows[0] keys: {list(rows[0].keys())}")
        stats = rows[0].get("statistics", {})
        print(f"rows[0].statistics: {stats}")
        print(f"rows[0].participated: {rows[0].get('participated')}")
        print(f"rows[0].minutes: {stats.get('minutes')}")
        
