import json
import glob
import os

# 1. Identify SRS-only leagues
leagues_adv = set()
all_leagues = {} # league_id -> name

for f in glob.glob('data/basketball/universal_predictions_*.json'):
    try:
        with open(f, encoding='utf-8') as file:
            data = json.load(file)
            for p in data.get('predictions', []):
                lid = p.get('league_id')
                name = f"{p.get('country')} — {p.get('league')}"
                if lid:
                    all_leagues[lid] = name
                if 'ADVANCED' in str(p.get('model_architecture', '')):
                    leagues_adv.add(lid)
    except Exception:
        pass

srs_only_ids = [lid for lid in all_leagues if lid not in leagues_adv]

# 2. Diagnose each SRS-only league
missing_config = []
empty_url = []
missing_data = [] # Scraper didn't produce a file
team_mismatch = [] # Scraper produced a file but generate_advanced_metrics probably couldn't match teams

for lid in srs_only_ids:
    name = all_leagues[lid]
    config_path = f"configs/leagues/{lid}.json"
    
    if not os.path.exists(config_path):
        missing_config.append(f"{lid} | {name}")
        continue
        
    try:
        with open(config_path, encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception:
        missing_config.append(f"{lid} | {name} (Config Unreadable)")
        continue
        
    url = cfg.get("proballers_url", "")
    if not url:
        empty_url.append(f"{lid} | {name}")
        continue
        
    pb_name = cfg.get("proballers_name", "")
    pb_file = f"data/historical/proballers_{pb_name}.json"
    
    if not os.path.exists(pb_file):
        missing_data.append(f"{lid} | {name}")
        continue
        
    # File exists. Let's check if it actually has stats
    try:
        with open(pb_file, encoding='utf-8') as f:
            pb_data = json.load(f)
            if not pb_data:
                missing_data.append(f"{lid} | {name} (Empty Proballers Data)")
            else:
                team_mismatch.append(f"{lid} | {name} (Data exists, probably Team Name Mismatch)")
    except Exception:
        missing_data.append(f"{lid} | {name} (Corrupt Proballers Data)")

print("\n--- DIAGNOSIS OF 98 SRS-ONLY LEAGUES ---")
print(f"\n1. MISSING CONFIG FILE ({len(missing_config)} leagues)")
print("   (These leagues have not been mapped to a Proballers URL at all in configs/leagues/)")
for x in missing_config[:10]: print(f"   - {x}")
if len(missing_config) > 10: print("   ... and more.")

print(f"\n2. CONFIG EXISTS BUT EMPTY URL ({len(empty_url)} leagues)")
print("   (The JSON config exists, but the 'proballers_url' is blank)")
for x in empty_url[:10]: print(f"   - {x}")

print(f"\n3. SCKRAPER FAILED OR NO DATA ({len(missing_data)} leagues)")
print("   (We have a URL, but scrape_proballers.py didn't find data or didn't run for it)")
for x in missing_data: print(f"   - {x}")

print(f"\n4. TEAM NAME MISMATCH OR OTHER FAILURES ({len(team_mismatch)} leagues)")
print("   (Data was scraped successfully, but the ADVANCED model couldn't use it. Usually because API team names don't match Proballers team names)")
for x in team_mismatch: print(f"   - {x}")
print()
