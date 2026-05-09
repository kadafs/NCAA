import json
import csv
import os

def run_comparison():
    json_file = "data/basketball/universal_predictions_2026-05-07.json"
    csv_file = "data/confidence_reports/confidence_2026-05-07.csv"
    
    with open(json_file, encoding='utf-8') as f:
        j_data = json.load(f)
    with open(csv_file, encoding='utf-8') as f:
        c_data = list(csv.DictReader(f))
        
    print(f"Total JSON predictions: {len(j_data.get('predictions', []))}")
    print(f"Total CSV rows: {len(c_data)}")
    
    # 1. How many JSON games are valid?
    json_valid = []
    for p in j_data.get("predictions", []):
        h_s = p.get("actual_home_score")
        if h_s is None: continue
        
        stage = p.get("stage", "")
        if stage is None: stage = ""
        stage = stage.lower()
        if any(k in stage for k in ["final", "semi", "quarter", "playoff", "3rd place", "relegation"]):
            continue
            
        json_valid.append(p)
        
    print(f"Valid JSON games (graded & non-playoff): {len(json_valid)}")
    
    # 2. How many CSV games are valid?
    csv_valid = []
    # To grade CSV games, we need to look up actuals in JSON
    j_map = {(p.get("home_team"), p.get("away_team")): p for p in j_data.get("predictions", [])}
    for r in c_data:
        h = r["home_team"]
        a = r["away_team"]
        p = j_map.get((h, a))
        if not p: continue
        if p.get("actual_home_score") is None: continue
        
        stage = p.get("stage", "")
        if stage is None: stage = ""
        stage = stage.lower()
        if any(k in stage for k in ["final", "semi", "quarter", "playoff", "3rd place", "relegation"]):
            continue
            
        csv_valid.append((r, p))
        
    print(f"Valid CSV games (found in JSON, graded & non-playoff): {len(csv_valid)}")
    
    # Let's count [LOW] hits for both
    j_low = 0
    j_low_hits = 0
    for p in json_valid:
        band = p.get("confidence_score_band") or p.get("band", "[UNKNOWN]")
        if "LOW" in band:
            j_low += 1
            if (p["actual_home_score"] + p["actual_away_score"]) >= (float(p["model_total"]) - 5):
                j_low_hits += 1
                
    c_low = 0
    c_low_hits = 0
    for r, p in csv_valid:
        band = r.get("band", "[UNKNOWN]")
        if "LOW" in band:
            c_low += 1
            if (p["actual_home_score"] + p["actual_away_score"]) >= (float(r["model_total"]) - 5):
                c_low_hits += 1

    print(f"JSON [LOW] tier hits: {j_low_hits}/{j_low}")
    print(f"CSV [LOW] tier hits: {c_low_hits}/{c_low}")

if __name__ == "__main__":
    run_comparison()
