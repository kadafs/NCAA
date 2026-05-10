from playwright.sync_api import sync_playwright

def intercept_nbl1():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Intercept network requests
        requests_found = []
        page.on("request", lambda request: requests_found.append(request.url))
        
        print("[*] Loading NBL1 fixtures...")
        page.goto("https://nbl1.com.au/fixtures?tab=results", wait_until='networkidle')
        page.wait_for_timeout(5000)
        
        print(f"[*] Total requests: {len(requests_found)}")
        for url in requests_found:
            if "sportradar" in url and "fixture" in url:
                print(f"  {url}")
                
        browser.close()

if __name__ == "__main__":
    intercept_nbl1()
