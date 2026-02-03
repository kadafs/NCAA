# Prediction System: Health Check Utility
import os
import json
import time
from datetime import datetime
import sys

def check_file(path, critical=False):
    if not os.path.exists(path):
        status = "❌ MISSING" if critical else "⚠️ MISSING"
        return status, "No file found"
    
    mtime = os.path.getmtime(path)
    age_hours = (time.time() - mtime) / 3600
    mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    
    if age_hours > 24:
        return "⚠️ STALE", f"Modified {age_hours:.1f} hours ago ({mtime_str})"
    return "✅ OK", f"Modified {age_hours:.1f} hours ago"

def validate_ncaa_stats(path):
    if not os.path.exists(path): return "❌ Error: File missing"
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            if not data: return "❌ Error: Empty file"
            
            # Check for BartTorvik defaults
            sample = list(data.values())[:3]
            for s in sample:
                if s.get('efg') == 50.0 and s.get('to') == 18.0:
                    return "⚠️ WARNING: Using hardcoded defaults (50/18/28/30)"
            return f"✅ OK ({len(data)} teams, live metrics detected)"
    except Exception as e:
        return f"❌ Error: {e}"

def validate_nba_stats(path):
    if not os.path.exists(path): return "⚠️ Missing"
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            if not data: return "❌ Error: Empty file"
            
            # Check for 30 teams
            if len(data) < 30:
                return f"⚠️ Only {len(data)} teams found (expected 30)"
            return f"✅ OK (30 teams)"
    except Exception as e:
        return f"❌ Error: {e}"

def main():
    print("\n" + "="*60)
    print("🏀 SYSTEM INTEGRITY HEALTH CHECK")
    print("="*60)
    
    # 1. NCAA Layer
    print("\n--- NCAA DATA LAYER ---")
    st, msg = check_file("data/barttorvik_stats.json", critical=True)
    print(f"{'BartTorvik Stats':20} : {st:10} | {msg}")
    print(f"{'Metric Quality':20} : {validate_ncaa_stats('data/barttorvik_stats.json')}")
    
    st, msg = check_file("data/consolidated_stats.json")
    print(f"{'PPG/Scoring':20} : {st:10} | {msg}")
    
    # 2. NBA Layer
    print("\n--- NBA DATA LAYER ---")
    st, msg = check_file("data/nba_stats.json")
    print(f"{'NBA Team Stats':20} : {st:10} | {msg}")
    print(f"{'Team Coverage':20} : {validate_nba_stats('data/nba_stats.json')}")
    
    st, msg = check_file("data/nba_player_stats.json")
    print(f"{'NBA Player Stats':20} : {st:10} | {msg}")

    # 3. Market Layer
    print("\n--- MARKET & ODDS LAYER ---")
    odds_st = "✅ LIVE" if os.environ.get('SUPABASE_URL') else "⚠️ LOCAL ONLY"
    print(f"{'Centralized Odds':20} : {odds_st}")
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    csv_path = f"data/ncaa_market_{date_str}.csv"
    if os.path.exists(csv_path):
        print(f"{'Manual CSV':20} : ✅ DETECTED ({csv_path})")
    else:
        print(f"{'Manual CSV':20} : ℹ️ Not currently active for {date_str}")

    print("\n" + "="*60)
    print("SUGGESTIONS:")
    print("- If NCAA metrics are STALE/DEFAULT: run 'python ncaa/fetch_barttorvik.py'")
    print("- If NBA data is MISSING/STALE: run 'python nba/fetch_nba_stats.py'")
    print("- If Dashboard is wrong: check GitHub Actions logs for push errors.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
