import requests
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.ssl_adapter import get_robust_session

def test():
    url = "https://ncaa-api-w2ry.onrender.com/standings/basketball-men/d1"
    http = get_robust_session(retries=3)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    print(f"Testing connection to {url}")
    try:
        response = http.get(url, headers=headers, timeout=10)
        print(f"Success! Status: {response.status_code}")
    except Exception as e:
        print(f"Caught expected error: {e}")
        
        print("\nTesting fallback with verify=False on session...")
        try:
            response = http.get(url, headers=headers, timeout=10, verify=False)
            print(f"Fallback Success! Status: {response.status_code}")
        except Exception as e2:
            print(f"Fallback Failed as expected: {e2}")

        print("\nTesting fallback with requests.get(verify=False)...")
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            print(f"Direct requests.get fallback Success! Status: {response.status_code}")
        except Exception as e3:
            print(f"Direct requests.get fallback Failed: {e3}")

if __name__ == "__main__":
    test()
