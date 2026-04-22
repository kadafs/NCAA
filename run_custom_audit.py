import json
import os
import glob
from collections import defaultdict
import argparse

# ==========================================
# CONFIGURATION
# ==========================================
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'basketball')
TRACKING_EPOCH = '2026-03-25'

def load_valid_leagues():
    """Load leagues that have at least 5 graded games to filter out noise/exhibitions."""
    valid_leagues = set()
    lb_path = os.path.join(DATA_DIR, 'league_leaderboard.json')
    if os.path.exists(lb_path):
        with open(lb_path, 'r', encoding='utf-8') as f:
            for entry in json.load(f).get('leaderboard', []):
                adv_g = (entry.get('adv') or {}).get('graded_totals', 0)
                srs_g = (entry.get('srs') or {}).get('graded_totals', 0)
                if max(adv_g, srs_g) >= 5 and entry.get('league_id'):
                    valid_leagues.add(str(entry.get('league_id')))
    return valid_leagues

def run_audit(search_term):
    """Run an audit for a specific league or team name."""
    valid_leagues = load_valid_leagues()
    
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
    files = [f for f in all_files if os.path.basename(f).replace('universal_predictions_','').replace('.json','') >= TRACKING_EPOCH]
    
    # stats[tier] = {'total': 0, 'wins_flat': 0, 'wins_5': 0, 'wins_10': 0}
    stats = defaultdict(lambda: {'total': 0, 'wins_flat': 0, 'wins_5': 0, 'wins_10': 0})
    
    search_lower = search_term.lower().strip()
    games_found = 0
    matched_names = set()
    
    for p_file in files:
        if not os.path.exists(p_file): continue
        with open(p_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for p in data.get('predictions', []):
            if str(p.get('league_id')) not in valid_leagues: continue
            
            # Format strings for searching, normalizing dashes
            league_str = f"{p.get('country', '')} - {p.get('league', '')}".lower().replace('\u2014', '-')
            home_str = p.get('home_team', '').lower().replace('\u2014', '-')
            away_str = p.get('away_team', '').lower().replace('\u2014', '-')
            
            # Check if search term matches league, home team, or away team
            is_match = False
            if search_lower in league_str:
                is_match = True
                matched_names.add(f"{p.get('country', '')} - {p.get('league', '')}".upper())
            elif search_lower in home_str:
                is_match = True
                matched_names.add(p.get('home_team'))
            elif search_lower in away_str:
                is_match = True
                matched_names.add(p.get('away_team'))
                
            if not is_match:
                continue
                
            act_h = p.get('actual_home_score')
            act_a = p.get('actual_away_score')
            model_total = p.get('model_total')
            
            # Require graded games
            if act_h is None or act_a is None or not model_total: continue
            
            h_vol = p.get('home_team_volatility')
            a_vol = p.get('away_team_volatility')
            if h_vol is None or a_vol is None: continue
            
            # Determine Tier
            if h_vol < 14.8 and a_vol < 14.8:
                tier = 1
            elif h_vol <= 16.6 and a_vol <= 16.6:
                tier = 2
            elif h_vol > 16.6 and a_vol > 16.6:
                tier = 4
            else:
                tier = 3
                
            actual_total = act_h + act_a
            
            stats[tier]['total'] += 1
            if actual_total >= model_total:
                stats[tier]['wins_flat'] += 1
            if actual_total >= (model_total - 5):
                stats[tier]['wins_5'] += 1
            if actual_total >= (model_total - 10):
                stats[tier]['wins_10'] += 1
                
            games_found += 1
            
    # --- OUTPUT ---
    print("\n" + "="*80)
    print(f" AUDIT REPORT: '{search_term.upper()}'")
    if matched_names:
        matches_list = list(matched_names)[:5]
        if len(matched_names) > 5:
            matches_list.append(f"...and {len(matched_names)-5} more")
        print(f" Matched entities: {', '.join(matches_list)}")
    print("="*80)
    
    if games_found == 0:
        print("\n  [X] No graded games found matching this search term since the tracking epoch.")
        print("  Check the spelling or try a broader search.\n")
        return
        
    tier_names = {
        1: 'Tier 1 (Both Green)',
        2: 'Tier 2 (Both Colored)',
        3: 'Tier 3 (One Unstable)',
        4: 'Tier 4 (Both Unstable)'
    }
    
    print(f'\n{"Stability Tier":<24} | {"Games":>5} | {"Flat Floor":>15} | {"-5 Points":>15} | {"-10 Points":>15}')
    print('-' * 82)
    
    total_games = 0
    total_flat = 0
    total_5 = 0
    total_10 = 0
    
    for t in range(1, 5):
        d = stats[t]
        tot = d['total']
        total_games += tot
        total_flat += d['wins_flat']
        total_5 += d['wins_5']
        total_10 += d['wins_10']
        
        if tot == 0:
            print(f'{tier_names[t]:<24} | {tot:>5} | {"-":>15} | {"-":>15} | {"-":>15}')
            continue
            
        pct_flat = (d['wins_flat'] / tot) * 100
        pct_5 = (d['wins_5'] / tot) * 100
        pct_10 = (d['wins_10'] / tot) * 100
        
        flat_str = f"{d['wins_flat']}/{tot} ({pct_flat:.0f}%)"
        str_5 = f"{d['wins_5']}/{tot} ({pct_5:.0f}%)"
        str_10 = f"{d['wins_10']}/{tot} ({pct_10:.0f}%)"
        
        print(f'{tier_names[t]:<24} | {tot:>5} | {flat_str:>15} | {str_5:>15} | {str_10:>15}')
        
    print('-' * 82)
    
    # Print Totals
    if total_games > 0:
        pct_flat = (total_flat / total_games) * 100
        pct_5 = (total_5 / total_games) * 100
        pct_10 = (total_10 / total_games) * 100
        
        flat_str = f"{total_flat}/{total_games} ({pct_flat:.0f}%)"
        str_5 = f"{total_5}/{total_games} ({pct_5:.0f}%)"
        str_10 = f"{total_10}/{total_games} ({pct_10:.0f}%)"
        
        print(f'{"OVERALL":<24} | {total_games:>5} | {flat_str:>15} | {str_5:>15} | {str_10:>15}')
    print("\n")

def main():
    parser = argparse.ArgumentParser(description="Run a custom audit for a specific team or league.")
    parser.add_argument("query", nargs="*", help="The name of the league or team to search for.")
    args = parser.parse_args()
    
    # If passed as an argument, run it and exit
    if args.query:
        search_term = " ".join(args.query)
        run_audit(search_term)
        return
        
    # Interactive mode
    print("\n🏀 NCAA-API Custom Audit Tool")
    print("Type a League Name (e.g. 'Spain Primera') or Team Name (e.g. 'Zalgiris')")
    print("Type 'exit' or 'quit' to close.\n")
    
    while True:
        try:
            search_term = input("Search > ")
            if search_term.lower().strip() in ['exit', 'quit', 'q']:
                break
            if not search_term.strip():
                continue
            run_audit(search_term)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError: {e}\n")

if __name__ == "__main__":
    main()
