import requests
import json

def dump_odds():
    url = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa"
    print(f"Fetching from: {url}")
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                print(f"Keys found: {len(data)}")
                for k in sorted(data.keys()):
                    if "Dakota" in k or "Thomas" in k or "Mary" in k:
                        print(f"  MATCH: '{k}' -> {data[k]}")
            else:
                print("Data is not a dict")
        else:
            print(f"Failed: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_odds()
