import sys
import os
import json
import requests
from datetime import datetime
import argparse

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.append(ROOT_DIR)

from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

def fetch_scores_espn(date_str):
    """Fetch completed NCAA D1 scores from ESPN for any date (historical or live)."""
    try:
        espn_date = date_str.replace("-", "")
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={espn_date}&limit=500&groups=50"
        resp = requests.get(url, timeout=15)
        data = resp.json()

        live_games = {}
        for event in data.get('events', []):
            comp = event['competitions'][0]
            home_comp = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
            away_comp = next(c for c in comp['competitors'] if c['homeAway'] == 'away')

            home_name = home_comp['team']['shortDisplayName']
            away_name = away_comp['team']['shortDisplayName']
            state = event['status']['type']['state']  # 'pre', 'in', 'post'
            period = event['status'].get('period', 0)
            clock = event['status'].get('displayClock', '')

            def safe_int(val):
                try:
                    return int(val) if val else 0
                except (ValueError, TypeError):
                    return 0

            info = {
                "status": "FINAL" if state == 'post' else ("IN_PROGRESS" if state == 'in' else "SCHEDULED"),
                "period": f"Final" if state == 'post' else (f"H{period} {clock}" if state == 'in' else ""),
                "score_h": safe_int(home_comp.get('score', 0)),
                "score_a": safe_int(away_comp.get('score', 0)),
            }
            live_games[home_name] = info
            live_games[away_name] = info
        return live_games
    except Exception as e:
        print(f"ESPN fetch failed: {e}")
        return {}

def load_predictions(path):
    if not os.path.exists(path):
        print(f"Error: Prediction file not found at {path}")
        return None
    with open(path, "r") as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=None, help="Path to predictions JSON (overrides defaults)")
    parser.add_argument("--date", help="Override Date (YYYY-MM-DD)")
    parser.add_argument("--include-pass", action="store_true", help="Include PASS decisions in audit (grades as if betting against the edge)")
    parser.add_argument("--d1-hybrid", action="store_true", help="Audit D1 Hybrid predictions (d1_hybrid_predictions.json)")
    parser.add_argument("--no-injuries", action="store_true", help="Audit D1 Conf No-Injuries predictions (d1_conf_predictions_no_injuries.json)")
    args = parser.parse_args()

    # Resolve prediction file and label
    if args.file:
        pred_file = args.file
        label = "D1 PREDICTION AUDITOR"
    elif args.no_injuries:
        pred_file = os.path.join(ROOT_DIR, "data", "d1_conf_predictions_no_injuries.json")
        label = "D1 CONF (NO INJURIES) PREDICTION AUDITOR"
    elif args.d1_hybrid:
        pred_file = os.path.join(ROOT_DIR, "data", "d1_hybrid_predictions.json")
        label = "D1 HYBRID PREDICTION AUDITOR"
    else:
        pred_file = os.path.join(ROOT_DIR, "data", "d1_conf_predictions.json")
        label = "D1 PREDICTION AUDITOR"

    print("-" * 60)
    print(f" {label}")
    print("-" * 60)

    # 1. Load Predictions
    preds = load_predictions(pred_file)
    if not preds:
        return
    
    print(f"Loaded {len(preds)} pending predictions.")
    
    # 2. Determine Date
    if args.date:
        date_str = args.date
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        # Infer from first prediction if possible
        try:
            ts = preds[0]['timestamp']
            dt = datetime.fromisoformat(ts)
            date_str = dt.strftime("%Y-%m-%d")
            print(f"Using date from predictions: {date_str}")
        except:
            dt = datetime.now()
            date_str = dt.strftime("%Y-%m-%d")
            print(f"Using default date (Today): {date_str}")

    # 3. Fetch Actual Scores via ESPN (works for historical dates too)
    print(f"Fetching scores for {date_str} via ESPN...")
    live_games = fetch_scores_espn(date_str)

    if not live_games:
        print("No games found from ESPN.")
        return

    # 4. Compare
    wins = 0
    losses = 0
    pending = 0
    
    print("\n" + "=" * 100)
    print(f"{'MATCHUP':<35} | {'PRED':<10} | {'MODEL':<6} | {'LINE':<6} | {'SCORE':<8} | {'RESULT':<10}")
    print("-" * 100)

    for p in preds:
        # Determine bet type from decision and edge
        # PLAY/LEAN with positive edge = OVER, negative edge = UNDER
        # PASS with --include-pass: grade as if we bet the side that would have been recommended
        bet_type = "PASS"
        decision = p.get('decision', 'PASS')
        edge = p.get('edge', 0)
        
        if decision in ['PLAY', 'LEAN']:
            # Check if edge is a valid number (not NaN)
            try:
                edge_val = float(edge)
                if edge_val > 0:
                    bet_type = "OVER"
                elif edge_val < 0:
                    bet_type = "UNDER"
            except (ValueError, TypeError):
                # NaN or invalid edge, skip
                pass
        elif decision == 'PASS' and args.include_pass:
            # For PASS decisions, determine which side had the edge
            # We'll grade it as "did we correctly avoid this bet?"
            try:
                edge_val = float(edge)
                if abs(edge_val) > 0.5:  # Only grade if there was a meaningful edge
                    if edge_val > 0:
                        bet_type = "PASS_OVER"  # Model said pass, but edge was OVER
                    elif edge_val < 0:
                        bet_type = "PASS_UNDER"  # Model said pass, but edge was UNDER
            except (ValueError, TypeError):
                pass
        
        if bet_type == "PASS":
            continue

        # Look for game
        # Need to match p['home'] (Predicted Name) to Live Name using find_team
        # This is tricky because find_team maps TO a canonical name.
        # But live_games keys are RAW names.
        # We need to map Live Keys -> Canonical -> Match.
        
        # Simpler: Just iterate live_games and check if p['home'] is loosely in key
        found_game = None
        
        # Try finding live key that matches our prediction home team
        # Canonical names in preds are cleaner.
        # We can try find_team_in_dict logic but reversed? No.
        
        # Heuristic: Check if p['home'] is in live_games keys
        # The keys in live_games are from NCAA API (e.g. "Duke").
        # p['home'] is from Barttorvik (e.g. "Duke").
        
        # Let's try direct lookup first
        if p['home'] in live_games:
            found_game = live_games[p['home']]
        elif p['away'] in live_games:
            found_game = live_games[p['away']]
        else:
            # Fuzzy Logic
            for k, v in live_games.items():
                if k in p['home'] or p['home'] in k:
                    found_game = v
                    break
        
        market_line = p['market_total']
        model_total = p.get('model_total', 0)
        
        # Format model total for display
        try:
            model_str = f"{float(model_total):.1f}" if model_total and str(model_total) != 'nan' else "N/A"
        except (ValueError, TypeError):
            model_str = "N/A"
        
        if not found_game:
            print(f"{p['matchup']:<35} | {bet_type:<10} | {model_str:<6} | {market_line:<6} | {'???':<8} | Not Found")
            continue
            
        final_score = found_game['score_h'] + found_game['score_a']
        status = found_game['status']
        period = found_game.get('period', '')
        
        res_str = "PENDING"
        
        # Check if game is final (status or period may contain "FINAL")
        is_final = "FINAL" in status.upper() or "FINAL" in str(period).upper()
        
        if is_final:
            if bet_type == "OVER":
                if final_score > market_line:
                    res_str = "WIN"
                    wins += 1
                elif final_score < market_line:
                    res_str = "LOSS"
                    losses += 1
                else:
                    res_str = "PUSH"
            elif bet_type == "UNDER":
                if final_score < market_line:
                    res_str = "WIN"
                    wins += 1
                elif final_score > market_line:
                    res_str = "LOSS"
                    losses += 1
                else:
                    res_str = "PUSH"
            elif bet_type.startswith("PASS_"):
                # For PASS decisions, a "win" means we correctly avoided a losing bet
                # i.e., if edge suggested OVER but we passed, we "win" if UNDER would have won
                if bet_type == "PASS_OVER":
                    if final_score < market_line:
                        res_str = "GOOD PASS"  # Correctly avoided a losing OVER
                        wins += 1
                    else:
                        res_str = "BAD PASS"  # Should have bet OVER
                        losses += 1
                elif bet_type == "PASS_UNDER":
                    if final_score > market_line:
                        res_str = "GOOD PASS"  # Correctly avoided a losing UNDER
                        wins += 1
                    else:
                        res_str = "BAD PASS"  # Should have bet UNDER
                        losses += 1
        else:
            res_str = f"In Prog ({period})"
            pending += 1

        print(f"{p['matchup']:<35} | {bet_type:<10} | {model_str:<6} | {market_line:<6} | {final_score:<8} | {res_str}")

    print("-" * 100)
    print(f"AUDIT COMPLETE")
    print(f"Wins: {wins} | Losses: {losses} | Pending: {pending}")
    if wins + losses > 0:
        print(f"Win Rate: {wins / (wins + losses):.1%}")
    print("-" * 100)

if __name__ == "__main__":
    main()
