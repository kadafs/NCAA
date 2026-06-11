import os
import json
import argparse
from run_daily_f5 import get_team_bullpen_fip

def evaluate_bullpens(json_filename=".consensus_f5_v3_report.json"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, json_filename)
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        print("Make sure you run consensus_f5_v3.py (or v2) first!")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"==================================================")
    print(f"📊 BULLPEN POST-PROCESSING MODULE 📊")
    print(f"Evaluating late-inning environments for flagged games...")
    print(f"Source: {json_filename}")
    print(f"==================================================\n")
    
    evaluated_count = 0
    
    for game in data:
        away = game['away_team']
        home = game['home_team']
        
        # Determine signals
        is_fg_over = False
        is_f5_under = False
        
        for adv in [game['adv_3_5'], game['adv_4_5'], game['adv_5_5']]:
            if "FULL GAME OVER" in adv and "(HIGH)" in adv:
                is_fg_over = True
            elif "FULL GAME OVER" in adv:
                is_fg_over = True
                
            if "Bet **UNDER**" in adv and "(HIGH)" in adv:
                is_f5_under = True
            elif "Bet **UNDER**" in adv:
                is_f5_under = True
                
        if not is_fg_over and not is_f5_under:
            continue # Skip games with no recommended bets
            
        evaluated_count += 1
        print(f"### ⚾ {away} @ {home}")
        
        try:
            # Bullpen FIP fetches are heavily cached, so this is instant
            away_bp = get_team_bullpen_fip(away, sport_id=1)
            home_bp = get_team_bullpen_fip(home, sport_id=1)
            avg_bp = round((away_bp + home_bp) / 2, 2)
        except Exception as e:
            print(f"  [!] Failed to fetch bullpen data: {e}\n")
            continue
            
        print(f"  ➤ Bullpen FIPs: {away} ({away_bp}) | {home} ({home_bp})")
        print(f"  ➤ Combined Avg: {avg_bp}")
        
        if is_fg_over:
            print(f"  🎯 F5 Signal: FULL GAME OVER")
            if avg_bp >= 4.20:
                print("  🟢 UPGRADE (ELITE OVER ENVIRONMENT): Both bullpens are highly vulnerable. Late innings will bleed runs.")
            elif avg_bp <= 3.60:
                print("  🔴 DOWNGRADE (RISKY LATE INNINGS): Elite lockdown arms present. High risk of scoreless innings 6-9.")
            else:
                print("  ⚪ NEUTRAL: Average bullpen environment. Rely on starting pitching edge.")
                
        if is_f5_under:
            print(f"  🎯 F5 Signal: UNDER")
            if avg_bp >= 4.20:
                print("  ⚠️ DANGER: Terrible bullpens. Stick STRICTLY to the F5 Under. Full Game Under is highly vulnerable.")
            elif avg_bp <= 3.60:
                print("  🟢 UPGRADE (SAFE UNDER): Elite bullpens. Safe to bet the Full Game Under as well.")
            else:
                print("  ⚪ NEUTRAL: Average bullpen environment. F5 Under is standard play.")
        print("")
        
    if evaluated_count == 0:
        print("No betting edges found in the report. No bullpens to evaluate.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post-process F5 outputs to evaluate bullpen strength")
    parser.add_argument('--file', type=str, default=".consensus_f5_v3_report.json", 
                        help="The JSON file to read (default: .consensus_f5_v3_report.json)")
    args = parser.parse_args()
    
    evaluate_bullpens(args.file)
