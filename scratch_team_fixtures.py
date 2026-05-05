import requests, json

BASE = 'https://embed-api.eui.connect.sportradar.com/v1/embed/3'

# Test one team key as fixture_detail to see what the response looks like
key = 'fccd628c-38b7-11ee-aafd-0fd86aac2a3b'
url = f'{BASE}/fixture_detail?fixtureId={key}'
r = requests.get(url, timeout=8)
data = r.json().get('data', {})

print("Top-level keys:", list(data.keys())[:15])
print()

# Check each top-level key for game/fixture references
for top_key in data.keys():
    val = data[top_key]
    if isinstance(val, dict):
        inner = list(val.keys())[:5]
        print(f"  data.{top_key} (dict): {inner}")
    elif isinstance(val, list) and val:
        print(f"  data.{top_key} (list[{len(val)}]): first item keys: {list(val[0].keys())[:5] if isinstance(val[0], dict) else val[:3]}")
    else:
        print(f"  data.{top_key}: {val}")

print()
# specifically look for fixture/season info
banner = data.get('banner', {})
print("Banner keys:", list(banner.keys()))
fixture_info = banner.get('fixture', {})
print("Fixture info:", json.dumps(fixture_info, indent=2)[:500])
