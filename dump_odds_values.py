import requests
import json

def dump_val():
    url = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            targets = ["Saint Francis", "Chicago State", "Southern Illinois", "Indiana State", "UTRGV", "Nicholls"]
            for k, v in data.items():
                if any(t.lower() in k.lower() for t in targets):
                    print(f"{k}: {v}")
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_val()
