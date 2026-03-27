import os
import time
import json
import requests
from datetime import datetime

ELO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "football", "elo_ratings.json")

def generate_elo_ratings(force=False):
    """
    Downloads international results from a public repository, 
    calculates Elo ratings, and saves them.
    Only runs if forced or if the cache is older than 30 days.
    """
    if not force and os.path.exists(ELO_FILE):
        age_days = (time.time() - os.path.getmtime(ELO_FILE)) / 86400
        if age_days < 30:
            return  # Cache is fresh enough (under 30 days old)
            
    print("  [ELO] Updating International Elo Ratings from latest results...")
    
    url = 'https://raw.githubusercontent.com/martj42/international_results/master/results.csv'
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            print("  [ELO] Failed to download results CSV.")
            return
    except Exception as e:
        print(f"  [ELO] Error downloading results: {e}")
        return

    lines = resp.text.strip().split('\n')[1:]
    ratings = {}
    
    def get_elo(team):
        return ratings.get(team, 1500)
        
    def expected(ra, rb):
        return 1 / (1 + 10 ** ((rb - ra) / 400))
        
    for line in lines:
        parts = line.split(',')
        if len(parts) >= 8:
            date, home, away, hg, ag, tourn, city, country = parts[:8]
            
            # Seed 2016-present to keep calculation fast and relevant
            if date < '2016-01-01': continue
            
            try:
                hg, ag = int(hg), int(ag)
            except ValueError:
                continue
                
            rh = get_elo(home)
            ra = get_elo(away)
            
            home_adv = 100 if home == country else 0
            
            eh = expected(rh + home_adv, ra)
            ea = expected(ra, rh + home_adv)
            
            # K-factor adjustments based on competition gravity
            if 'World Cup' in tourn: k = 60
            elif 'Continental' in tourn or 'Copa' in tourn or 'Euro' in tourn or 'Gold Cup' in tourn or 'AFCON' in tourn: k = 50
            elif 'qualification' in tourn.lower() or 'Nations League' in tourn: k = 40
            elif tourn == 'Friendly': k = 20
            else: k = 30
            
            if hg > ag: sh, sa = 1, 0
            elif hg == ag: sh, sa = 0.5, 0.5
            else: sh, sa = 0, 1
                
            gd = abs(hg - ag)
            gd_mult = 1
            if gd == 2: gd_mult = 1.5
            elif gd == 3: gd_mult = 1.75
            elif gd >= 4: gd_mult = 1.75 + (gd - 3) / 8.0
            
            ratings[home] = rh + k * gd_mult * (sh - eh)
            ratings[away] = ra + k * gd_mult * (sa - ea)
            
    final_ratings = {k: int(v) for k, v in ratings.items()}
    final_ratings = dict(sorted(final_ratings.items(), key=lambda item: item[1], reverse=True))
    
    output = {
        'updated_at': datetime.now().strftime('%Y-%m-%d'),
        'method': 'generated_from_martj42',
        'ratings': final_ratings
    }
    
    os.makedirs(os.path.dirname(ELO_FILE), exist_ok=True)
    with open(ELO_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        
    print(f"  [ELO] Saved updated ratings for {len(final_ratings)} teams.")
    
if __name__ == "__main__":
    generate_elo_ratings(force=True)
