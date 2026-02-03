import os
import sys
print("Starting isolation test...")
sys.path.append(os.getcwd())
print("Path appended.")
try:
    from utils.ssl_adapter import get_robust_session
    print("Imported get_robust_session.")
    http = get_robust_session(retries=1)
    print("Initialized session.")
    url = "https://ncaa-api-w2ry.onrender.com/standings/basketball-men/d1"
    print(f"Fetching {url}...")
    resp = http.get(url, timeout=10)
    print(f"Response status: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
print("Test finished.")
