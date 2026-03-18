import os
import json
import argparse
from datetime import datetime
import requests
from dotenv import load_dotenv

def get_api_headers():
    load_dotenv()
    api_key = os.getenv("API_BASKETBALL_KEY")
    if not api_key:
        api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        raise ValueError("Missing API key. Check .env file.")
    return {"x-apisports-key": api_key}

def fetch_actual_results(date_str):
    """Fetch all football fixtures for a specific date from API-Sports."""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = get_api_headers()
    params = {"date": date_str}
    
    print(f"Fetching actual results from API for {date_str}...")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"  [X] API Error: {response.status_code}")
        return {}
    
    data = response.json()
    if not data or 'response' not in data:
        print("  [X] No response data found.")
        return {}
        
    fixtures = {}
    for item in data['response']:
        # Extract meaningful data
        fixture_status = item['fixture']['status']['short']
        home_team = item['teams']['home']['name']
        away_team = item['teams']['away']['name']
        
        # Only care about completed games
        if fixture_status not in ['FT', 'AET', 'PEN']:
            continue
            
        home_goals = item['goals']['home']
        away_goals = item['goals']['away']
        
        if home_goals is None or away_goals is None:
            continue
            
        # Create a simplified key. We'll strip spaces and lowercase
        # because our JSON files might have slight variations like "Man Utd" vs "Manchester United"
        # We will attempt exact matches first, then fuzzy
        match_key = f"{home_team} @ {away_team}".lower()
        fixtures[match_key] = {
            'home_goals': home_goals,
            'away_goals': away_goals,
            'btts_hit': (home_goals > 0 and away_goals > 0),
            'draw_hit': (home_goals == away_goals),
            'scoreline': f"{home_goals}-{away_goals}"
        }
    
    print(f"  => Found {len(fixtures)} completed fixtures in API.")
    return fixtures

def load_predictions(date_str, specific_file=None):
    """Load JSON predictions from the data/football directory."""
    predictions = []
    data_dir = "data/football"
    
    if not os.path.exists(data_dir):
        return predictions

    if specific_file:
        file_path = specific_file if os.path.exists(specific_file) else os.path.join(data_dir, specific_file)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    records = json.load(f)
                    if isinstance(records, list):
                        date_records = [r for r in records if isinstance(r, dict) and r.get('date') == date_str]
                        predictions.extend(date_records)
                except json.JSONDecodeError:
                    pass
        else:
            print(f"  [X] Could not find specific file: {specific_file}")
            
        return predictions

    # Otherwise scan all files that end with expected patterns for that date
    # Usually this is the batch runner outputs:
    # high_scoring_predictions_2026-03-09.json
    # high_draw_predictions_2026-03-09.json
    # english_leagues_predictions_2026-03-09.json
    # sa_draw_predictions_2026-03-09.json
    # eu_scoring_predictions_2026-03-09.json
    
    # We also check individual league files if they contain the target date
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(data_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    records = json.load(f)
                    
                    if not isinstance(records, list):
                        continue
                        
                    # Filter records by date
                    date_records = [r for r in records if isinstance(r, dict) and r.get('date') == date_str]
                    
                    # Avoid duplicates (if a match is in both a single league file AND a batch file)
                    for dr in date_records:
                        if not any(p.get('matchup') == dr.get('matchup') for p in predictions):
                            predictions.append(dr)
                except json.JSONDecodeError:
                    continue
                    
    return predictions

def normalize_name(name):
    """Simple normalization for fuzzy matching if direct key fails."""
    return name.lower().replace("fc", "").replace("cd", "").replace(" ", "").strip()

def find_result_for_prediction(prediction, actuals):
    """Attempt to match a prediction record to the API actuals dictionary."""
    home_p = prediction.get('home_team', '')
    away_p = prediction.get('away_team', '')
    p_key = f"{home_p} @ {away_p}".lower()
    
    # 1. Exact match
    if p_key in actuals:
        return actuals[p_key]
        
    # 2. Matchup string match
    matchup_key = prediction.get('matchup', '').lower()
    if matchup_key in actuals:
        return actuals[matchup_key]
        
    # 3. Fuzzy search based on normalized names
    norm_home_p = normalize_name(home_p)
    norm_away_p = normalize_name(away_p)
    
    for a_key, a_data in actuals.items():
        if "@" in a_key:
            a_home, a_away = a_key.split(" @ ")
            if norm_home_p in normalize_name(a_home) and norm_away_p in normalize_name(a_away):
                return a_data
                
    return None

def main():
    parser = argparse.ArgumentParser(description="Audit Football Predictions vs Actual Results")
    parser.add_argument("--date", required=True, help="Target date in YYYY-MM-DD format (e.g. 2026-03-09)")
    parser.add_argument("--file", help="Specific JSON prediction file to audit (optional)")
    args = parser.parse_args()
    
    print("=" * 64)
    print(f" FOOTBALL AUDIT | Date: {args.date}")
    print("=" * 64)
    
    # 1. Load predictions
    predictions = load_predictions(args.date, args.file)
    if not predictions:
        print(f"[!] No predictions found for {args.date}.")
        return
        
    print(f"Loaded {len(predictions)} predictions for date.")
    
    # 2. Fetch actual results from API
    actuals = fetch_actual_results(args.date)
    if not actuals:
        print("[!] Cannot audit without actual match results.")
        return

    # 3. Grade
    btts_yes_w = 0
    btts_yes_l = 0
    btts_no_w = 0
    btts_no_l = 0
    draw_flag_w = 0
    draw_flag_l = 0
    
    league_stats = {}
    
    matched_count = 0
    
    print("\n" + "-" * 64)
    print(" MATCH REPORTS")
    print("-" * 64)
    
    for p in predictions:
        result = find_result_for_prediction(p, actuals)
        if not result:
            # Game might be postponed, or name mismatch too severe
            continue
            
        matched_count += 1
        
        matchup = p['matchup']
        league_name = p.get('league', 'Unknown').upper()
        decision = p['btts_decision']
        conf = p['btts_confidence']
        d_flag = p.get('draw_value_flag', False)
        
        if league_name not in league_stats:
            league_stats[league_name] = {
                'btts_yes_w': 0, 'btts_yes_l': 0,
                'btts_no_w': 0, 'btts_no_l': 0,
                'draw_w': 0, 'draw_l': 0
            }
        
        # Determine grades
        is_win = False
        grade_str = ""
        
        if decision == "PLAY YES":
            if result['btts_hit']:
                btts_yes_w += 1
                league_stats[league_name]['btts_yes_w'] += 1
                is_win = True
            else:
                btts_yes_l += 1
                league_stats[league_name]['btts_yes_l'] += 1
                
        elif decision in ("PLAY NO", "[STRONG] PLAY NO"):
            if not result['btts_hit']:
                btts_no_w += 1
                league_stats[league_name]['btts_no_w'] += 1
                is_win = True
            else:
                btts_no_l += 1
                league_stats[league_name]['btts_no_l'] += 1
                
        if d_flag:
            if result['draw_hit']:
                draw_flag_w += 1
                league_stats[league_name]['draw_w'] += 1
            else:
                draw_flag_l += 1
                league_stats[league_name]['draw_l'] += 1
                
        # Output visual log
        prefix = "[+]" if is_win else "[-]"
        if decision == "PASS":
            prefix = "[~]"
            
        print(f"\n{prefix} Match: {matchup} ({p['league'].upper()})")
        
        if decision != "PASS":
            win_txt = "WIN" if is_win else "LOSS"
            print(f"    Prediction: BTTS [{conf}] {decision} (Edge: {p['btts_edge']:+.1f}%)")
            print(f"    Result: {result['scoreline']} (BTTS: {'YES' if result['btts_hit'] else 'NO'}) -> {win_txt}")
        else:
            print(f"    Prediction: BTTS [{conf}] PASS")
            
        if d_flag:
            d_win_txt = "WIN" if result['draw_hit'] else "LOSS"
            print(f"    Draw Flag: YES (Fair Odds: {p['draw_fair_odds']}x)")
            print(f"    Result: {result['scoreline']} (Draw: {'YES' if result['draw_hit'] else 'NO'}) -> {d_win_txt}")

    # 4. Summary
    print("\n" + "=" * 64)
    print(" SUMMARY STATISTICS")
    print("=" * 64)
    print(f" Graded Matches: {matched_count} / {len(predictions)}")
    
    total_yes = btts_yes_w + btts_yes_l
    if total_yes > 0:
        win_pct = (btts_yes_w / total_yes) * 100
        # ROI assuming -110 juice flat betting
        # Win pays 0.909 U. Loss costs 1 U.
        roi_u = (btts_yes_w * 0.909) - btts_yes_l
        print(f" BTTS 'PLAY YES' : {btts_yes_w} W - {btts_yes_l} L ({win_pct:.1f}%) | {roi_u:+.2f} Units")
    else:
        print(" BTTS 'PLAY YES' : 0 Plays")
        
    total_no = btts_no_w + btts_no_l
    if total_no > 0:
        win_pct = (btts_no_w / total_no) * 100
        roi_u = (btts_no_w * 0.909) - btts_no_l
        print(f" BTTS 'PLAY NO'  : {btts_no_w} W - {btts_no_l} L ({win_pct:.1f}%) | {roi_u:+.2f} Units")
    else:
        print(" BTTS 'PLAY NO'  : 0 Plays")
        
    total_draw = draw_flag_w + draw_flag_l
    if total_draw > 0:
        win_pct = (draw_flag_w / total_draw) * 100
        req_odds = (total_draw / draw_flag_w) if draw_flag_w > 0 else 0
        print(f" DRAW FLAGS      : {draw_flag_w} W - {draw_flag_l} L ({win_pct:.1f}%) | Required avg odds {req_odds:.2f}x to break even")
    else:
        print(" DRAW FLAGS      : 0 Flags")
        
    print("=" * 64)

    # 5. League Leaderboard
    print("\n" + "=" * 80)
    print(" LEAGUE LEADERBOARD (Sorted by BTTS ROI)")
    print("=" * 80)
    
    league_results = []
    
    for lname, stats in league_stats.items():
        b_w = stats['btts_yes_w'] + stats['btts_no_w']
        b_l = stats['btts_yes_l'] + stats['btts_no_l']
        b_total = b_w + b_l
        roi = 0.0
        hit_rate = 0.0
        
        if b_total > 0:
            roi = (b_w * 0.909) - b_l
            hit_rate = (b_w / b_total) * 100
            
        league_results.append({
            'name': lname,
            'btts_plays': b_total,
            'btts_w': b_w,
            'btts_l': b_l,
            'hit_rate': hit_rate,
            'roi': roi,
            'draw_w': stats['draw_w'],
            'draw_l': stats['draw_l']
        })
        
    league_results.sort(key=lambda x: x['roi'], reverse=True)
    
    print(f"{'League':<30} | {'Plays':<5} | {'W-L':<6} | {'Hit %':<6} | {'ROI (U)':<8} | {'Draws (W-L)'}")
    print("-" * 80)
    
    for lr in league_results:
        total_actions = lr['btts_plays'] + lr['draw_w'] + lr['draw_l']
        if total_actions == 0:
            continue
            
        roi_str = f"{lr['roi']:+.2f}"
        hit_str = f"{lr['hit_rate']:.1f}%"
        wl_str = f"{lr['btts_w']}-{lr['btts_l']}"
        draw_str = f"{lr['draw_w']}-{lr['draw_l']}"
        
        # Truncate unusually long league names
        disp_name = (lr['name'][:27] + "...") if len(lr['name']) > 30 else lr['name']
        
        print(f"{disp_name:<30} | {lr['btts_plays']:<5} | {wl_str:<6} | {hit_str:<6} | {roi_str:<8} | {draw_str}")
        
    print("=" * 80)

if __name__ == "__main__":
    main()
