import sys
import os
import json
import time
from playwright.sync_api import sync_playwright

def scrape_one_league(url, browser):
    print(f"\n===========================================================")
    print(f"  STARTING FLASHSCORE SCRAPER: {url}")
    print(f"===========================================================")
    
    parts = [p for p in url.split("/") if p and p != "basketball"]
    slug = "custom_league"
    if len(parts) >= 2:
        slug = f"{parts[-2]}_{parts[-1]}"
        if slug.endswith("_results"):
            slug = f"{parts[-3]}_{parts[-2]}"
            
    slug = slug.replace("-", "_").replace(".", "")
    out_file = f"data/historical/flashscore_{slug}.json"
    
    if os.path.exists(out_file) and "--force" not in sys.argv:
        print(f"  -> SKIP: {out_file} already exists. (Use --force to overwrite)")
        return True

    page = browser.new_page()
    print("  -> Loading Flashscore Results layer...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        print(f"  -> ERROR loading page: {e}")
        page.close()
        return False
    
    try:
        page.click("button#onetrust-accept-btn-handler", timeout=2000)
        print("  -> Bypassed cookie overlay.")
    except:
        pass
        
    print("  -> Rapidly expanding hidden matches...")
    expansions = 0
    while True:
        try:
            more_link = page.locator("a.event__more.event__more--static")
            if more_link.is_visible(timeout=1500):
                more_link.click()
                expansions += 1
                time.sleep(0.5)
            else:
                break
        except Exception:
            break
            
    print(f"  -> Finished expanding {expansions} pagination blocks.")
    print("  -> Harvesting JSON box scores and Base IDs...")
    games = []
    
    match_elements = page.locator("div.event__match").all()
    for element in match_elements:
        try:
            match_id = element.get_attribute("id")
            if match_id and match_id.startswith("g_3_"):
                match_id = match_id[4:]
            else:
                match_id = None

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
                "match_id": match_id,
                "date": time_str,
                "home_team": home,
                "away_team": away,
                "home_score": int(home_score),
                "away_score": int(away_score),
                "advanced_stats": {}
            })
        except Exception:
            pass
            
    if len(games) == 0:
        print("  -> ERROR: 0 valid games found. The URL might be a broken API-slug translation (404 Page).")
        page.close()
        return False
        
    print(f"  -> Natively extracted {len(games)} basic box scores.")
    
    # DEEP SCRAPE HAS BEEN MIGRATED TO PROBALLERS.COM
    # Flashscore now exclusively provides the master baseline [SRS] final score arrays.

    page.close()
    
    os.makedirs("data/historical", exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"source_url": url, "total_games": len(games), "games": games}, f, indent=2)
        
    print(f"  -> Successfully packaged Advanced Dataset into: {out_file}\n")
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        if os.path.exists("batch_failed_urls.txt"):
            print("Usage: python scrape_flashscore.py <url1> [url2]...")
            print("       python scrape_flashscore.py $(cat batch_failed_urls.txt)")
            print("\nOptions:")
            print("  --fast    Skip advanced statistics (Rebounds, Turnovers) to run 10x faster.")
            print("  --force   Overwrite existing JSON files locally.")
        else:
            print("Usage: python scrape_flashscore.py <url1> [url2] [url3] ...")
        sys.exit(1)
        
    print(f"Initializing central Playwright pipeline to sequentially scrape {len(args)} leagues...")
    
    successful = []
    failed = []
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="playwright_profile2",
            headless=True,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        for url in args:
            try:
                if scrape_one_league(url, context):
                    successful.append(url)
                else:
                    failed.append(url)
            except Exception as e:
                print(f"  -> CRITICAL FAILURE ON LEAGUE: {url} | Error: {e}")
                failed.append(url)
        # Teardown physical engine cleanly
        context.close()
        
    print(f"\n===========================================================")
    print("  SCRAPING BATCH COMPLETE")
    print(f"  Successfully extracted:   {len(successful)} leagues")
    print(f"  Failed (404/Broken URL):  {len(failed)} leagues")
    print(f"===========================================================")
    
    if failed:
        with open("batch_failed_urls.txt", "w") as f:
            for u in failed:
                f.write(u + "\n")
        print("\n[!] IMPORTANT:")
        print("All broken URLs have been safely isolated and saved to -> 'batch_failed_urls.txt'")
        print("You can manually correct the spelling in that file, and then simply re-run those specific failures.")
    else:
        print("\nAll URLs translated and processed perfectly!")

if __name__ == "__main__":
    main()
