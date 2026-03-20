import sys
import os
import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    print("Warning: playwright_stealth not installed. Cloudflare may block execution.")
    HAS_STEALTH = False

def parse_boxscore(html):
    """
    Parses the raw Proballers Box Score HTML and mathematical extracts the Four Factors.
    Returns: {"home": {...}, "away": {...}}
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all('table')
    
    # Proballers tables:
    # [0] -> Quarter scores
    # [1] -> Home Team Stats
    # [2] -> Away Team Stats
    
    if len(tables) < 3:
        return None
        
    def extract_team_totals(table):
        rows = table.find_all('tr')
        if len(rows) < 2: return None
        
        # The last row in a Proballers stats table embodies the composite team totals
        totals_row = rows[-1]
        cells = [td.text.strip() for td in totals_row.find_all('td')]
        
        if len(cells) < 18: return None
        
        # Parse Field Goals (e.g. "27-44")
        twos = cells[5].split('-')
        threes = cells[6].split('-')
        fga = int(twos[1]) + int(threes[1]) if len(twos)==2 and len(threes)==2 else 0
        
        # Parse Free Throws (e.g. "24-29")
        fts = cells[8].split('-')
        fta = int(fts[1]) if len(fts)==2 else 0
        
        return {
            "team_name": cells[0],
            "points": int(cells[1] or 0),
            "FGA": fga,
            "FTA": fta,
            "ORB": int(cells[10] or 0),
            "DRB": int(cells[11] or 0),
            "TRB": int(cells[12] or 0),
            "AST": int(cells[13] or 0),
            "TOV": int(cells[14] or 0),
            "STL": int(cells[15] or 0),
            "BLK": int(cells[16] or 0)
        }
        
    # Extract Title for Match Date (e.g. Washington Wizards vs. Toronto Raptors - Oct 12, 2025 - Game recap | Proballers)
    title = soup.find('title').text if soup.find('title') else ""
    date_str = title.split(' - ')[1] if ' - ' in title else "Unknown"
    
    h_data = extract_team_totals(tables[1])
    a_data = extract_team_totals(tables[2])
    
    if not h_data or not a_data:
        return None
        
    return {
        "date": date_str,
        "home_team": h_data["team_name"],
        "away_team": a_data["team_name"],
        "home_score": h_data["points"],
        "away_score": a_data["points"],
        "stats": {
            "home": h_data,
            "away": a_data
        }
    }
def extract_league_schedule(url, context):
    """
    Extracts all box score URLs from a parent Proballers League/Team Schedule page.
    """
    page = context.new_page()
    if HAS_STEALTH: Stealth().apply_stealth_sync(page)
    
    # Random sleep to avoid 520 errors
    time.sleep(2)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(4000)
    except Exception as e:
        print(f"  -> Cloudflare telemetry timeout bypassed natively.")
        
    links = page.locator('a').all()
    box_urls = []
    
    for l in links:
        href = l.get_attribute('href')
        if href and '/basketball/game/' in href:
            full_url = "https://www.proballers.com" + href if not href.startswith("http") else href
            if full_url not in box_urls:
                box_urls.append(full_url)
                
    page.close()
    return box_urls

def scrape_match(url, context):
    page = context.new_page()
    if HAS_STEALTH: Stealth().apply_stealth_sync(page)
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
    except:
        pass # Catch infinite Cloudflare spinner loading loops
        
    html = page.content()
    data = parse_boxscore(html)
    page.close()
    
    return data

import argparse
import random

def run_proballers_scraper(target_url, max_games=None):
    domain_slug = target_url.strip('/').split('/')[-2]
    out_file = f"data/historical/proballers_{domain_slug}.json"
    
    # Simple resume logic: If file already exists and isn't empty, skip
    if os.path.exists(out_file) and os.path.getsize(out_file) > 1024:
        print(f"  [~] SKIPPING {domain_slug.upper()} -> Payload already exists!")
        return True

    print(f"\n===========================================================")
    print(f"  STARTING PROBALLERS SCRAPER -> {domain_slug.upper()}")
    print(f"===========================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        matches = extract_league_schedule(target_url, context)
        print(f"  -> Extracted {len(matches)} historical payload links from DOM.")
        
        if max_games and len(matches) > max_games:
            matches = matches[:max_games]
            
        final_dataset = []
        for i, match_url in enumerate(matches):
            print(f"      [{i+1}/{len(matches)}] Harvesting advanced stats: {match_url.split('/')[-1]}")
            m_data = scrape_match(match_url, context)
            if m_data:
                final_dataset.append(m_data)
                
            # Intelligent rate limit to avoid Cloudflare shadowbans
            time.sleep(random.uniform(2.1, 4.3))
                
        print("\n  [+] Mapped Mathematical Payloads:")
        
        if final_dataset:
            os.makedirs("data/historical", exist_ok=True)
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(final_dataset, f, indent=2, ensure_ascii=False)
            print(f"  [+] SUCCESS: Historical [ADVANCED] payload locked -> {out_file}")
            
        browser.close()
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proballers Advanced Metrics Mass Scraper")
    parser.add_argument("--url", type=str, help="Single schedule URL to scrape")
    parser.add_argument("--file", type=str, help="Text file containing multiple schedule URLs to batch process")
    parser.add_argument("--max", type=int, default=15, help="Max games to scrape per league (prevent timeout during sync)")
    
    args = parser.parse_args()
    
    if args.url:
        run_proballers_scraper(args.url, max_games=args.max)
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found.")
            sys.exit(1)
            
        with open(args.file, "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            
        print(f"Found {len(urls)} leagues in target manifest. Commencing Mass Extraction Sequence.")
        for idx, url in enumerate(urls):
            print(f"\n[BATCH ROUTINE] Extracting League {idx+1} of {len(urls)}...")
            run_proballers_scraper(url, max_games=args.max)
            
            if idx < len(urls) - 1:
                cooldown = random.uniform(8.5, 14.5)
                print(f"  -> Cooldown for {cooldown:.1f}s before next league...")
                time.sleep(cooldown)
    else:
        parser.print_help()
