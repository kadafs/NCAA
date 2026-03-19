import sys
import os
import json
import time
from playwright.sync_api import sync_playwright

def scrape_one_league(url, browser):
    print(f"\n===========================================================")
    print(f"  STARTING FLASHSCORE SCRAPER: {url}")
    print(f"===========================================================")
    
    # Intelligently construct a localized JSON filename based on the URL
    parts = [p for p in url.split("/") if p and p != "basketball"]
    slug = "custom_league"
    if len(parts) >= 2:
        slug = f"{parts[-2]}_{parts[-1]}"
        if slug.endswith("_results"):
            slug = f"{parts[-3]}_{parts[-2]}"
            
    slug = slug.replace("-", "_").replace(".", "")
    out_file = f"data/historical/flashscore_{slug}.json"
    
    # If the file already exists, don't waste time scraping it again
    if os.path.exists(out_file) and "--force" not in sys.argv:
        print(f"  -> SKIP: {out_file} already exists. (Use --force to overwrite)")
        return

    page = browser.new_page()
    print("  -> Loading Flashscore Results layer...")
    try:
        page.goto(url, wait_until="domcontentloaded")
    except Exception as e:
        print(f"  -> ERROR loading page: {e}")
        page.close()
        return
    
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
            time_str = element.locator(".event__time").inner_text().strip() if element.locator(".event__time").count() > 0 else ""
            home = element.locator(".event__participant--home").inner_text().strip()
            away = element.locator(".event__participant--away").inner_text().strip()
            
            home_score_el = element.locator(".event__score--home")
            away_score_el = element.locator(".event__score--away")
            
            if home_score_el.count() == 0 or away_score_el.count() == 0:
                continue
                
            home_score = home_score_el.inner_text().strip()
            away_score = away_score_el.inner_text().strip()
            
            if not home_score.isdigit() or not away_score.isdigit():
                continue

            games.append({
                "date": time_str,
                "home_team": home,
                "away_team": away,
                "home_score": int(home_score),
                "away_score": int(away_score)
            })
        except Exception:
            pass
            
    page.close()
    print(f"  -> Natively extracted {len(games)} valid games.")
    
    os.makedirs("data/historical", exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"source_url": url, "total_games": len(games), "games": games}, f, indent=2)
        
    print(f"  -> Successfully packaged dataset into: {out_file}\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python scrape_flashscore.py <url1> [url2] [url3] ...")
        sys.exit(1)
        
    print(f"Initializing central Playwright pipeline to sequentially scrape {len(args)} leagues...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for url in args:
            try:
                scrape_one_league(url, browser)
            except Exception as e:
                print(f"  -> CRITICAL FAILURE ON LEAGUE: {url} | Error: {e}")
        browser.close()
        
    print("FINISHED ALL BATCH SCRAPING!")


if __name__ == "__main__":
    main()
