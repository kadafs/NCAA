import sys
import os
import json
import time
from playwright.sync_api import sync_playwright

def scrape_flashscore(url):
    print(f"\n===========================================================")
    print(f"  STARTING FLASHSCORE SCRAPER: {url}")
    print(f"===========================================================")
    
    with sync_playwright() as p:
        print("  -> Launching headless Chromium browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("  -> Loading Flashscore Results layer...")
        page.goto(url, wait_until="domcontentloaded")
        
        # Opt-out of cookies if the popup blocks the view
        try:
            page.click("button#onetrust-accept-btn-handler", timeout=2000)
            print("  -> Bypassed cookie overlay.")
        except:
            pass
            
        # Natively click "Show more matches" until the entire season is revealed
        print("  -> Rapidly expanding hidden matches...")
        expansions = 0
        while True:
            try:
                more_link = page.locator("a.event__more.event__more--static")
                if more_link.is_visible(timeout=1500):
                    more_link.click()
                    expansions += 1
                    time.sleep(0.5) # Allow the React DOM to append the new nodes
                else:
                    break
            except Exception:
                break
                
        print(f"  -> Finished expanding {expansions} pagination blocks.")
        print("  -> Harvesting JSON box scores...")
        games = []
        
        # Extract row objects explicitly mapped inside the dynamic .event__match divs
        match_elements = page.locator("div.event__match").all()
        for element in match_elements:
            try:
                # Optional time string
                time_str = element.locator(".event__time").inner_text().strip() if element.locator(".event__time").count() > 0 else ""
                
                # Participant Labels
                home = element.locator(".event__participant--home").inner_text().strip()
                away = element.locator(".event__participant--away").inner_text().strip()
                
                # Score Labels
                home_score_el = element.locator(".event__score--home")
                away_score_el = element.locator(".event__score--away")
                
                # Exclude abandoned/postponed/canceled games
                if home_score_el.count() == 0 or away_score_el.count() == 0:
                    continue
                    
                home_score = home_score_el.inner_text().strip()
                away_score = away_score_el.inner_text().strip()
                
                # Ignore games that ended in letters (e.g., AWA, WO)
                if not home_score.isdigit() or not away_score.isdigit():
                    continue

                games.append({
                    "date": time_str,
                    "home_team": home,
                    "away_team": away,
                    "home_score": int(home_score),
                    "away_score": int(away_score)
                })
            except Exception as e:
                pass
                
        browser.close()
        
    print(f"  -> Natively extracted {len(games)} valid games.")
    
    # Intelligently construct a localized JSON filename based on the URL
    parts = [p for p in url.split("/") if p and p != "basketball"]
    slug = "custom_league"
    if len(parts) >= 2:
        # e.g. venezuela/superliga/results -> venezuela_superliga
        slug = f"{parts[-2]}_{parts[-1]}"
        if slug.endswith("_results"):
            slug = f"{parts[-3]}_{parts[-2]}"
            
    slug = slug.replace("-", "_").replace(".", "")
    
    os.makedirs("data/historical", exist_ok=True)
    out_file = f"data/historical/flashscore_{slug}.json"
    
    # Save the file using the Engine specification array
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"source_url": url, "total_games": len(games), "games": games}, f, indent=2)
        
    print(f"  -> Successfully packaged dataset into: {out_file}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape_flashscore.py <flashscore_url>")
        sys.exit(1)
    scrape_flashscore(sys.argv[1])
