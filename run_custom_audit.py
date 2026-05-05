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

def load_sdi_index():
    """Load the Star Dependency Index lookup dict {team_name_lower: sdi_record}.
    Also creates first-word and all-word aliases so short names (e.g. 'Cocodrilos',
    'Heidelberg') match full names (e.g. 'Cocodrilos de Caracas',
    'MLP Academics Heidelberg').
    """
    sdi_path = os.path.join(DATA_DIR, 'team_sdi.json')
    if not os.path.exists(sdi_path):
        return {}
    try:
        data = json.load(open(sdi_path, 'r', encoding='utf-8'))
        index = {}
        word_index = {}  # maps single significant words -> sdi_record
        STOP_WORDS = {'de', 'del', 'la', 'le', 'los', 'las', 'el', 'en', 'of', 'and',
                      'the', 'bc', 'bk', 'sk', 'fc', 'ac', 'sc', 'club', 'basket',
                      'basketball', 'sport', 'sports'}
        for t in data.get('teams', []):
            full_key = t['team'].lower()
            index[full_key] = t
            # First-word alias (e.g. 'cocodrilos' -> 'Cocodrilos de Caracas')
            words = full_key.split()
            first_word = words[0]
            if first_word not in index:
                index[first_word] = t
            # All significant word aliases (e.g. 'heidelberg' -> 'MLP Academics Heidelberg')
            for word in words:
                if len(word) >= 4 and word not in STOP_WORDS and word not in word_index:
                    word_index[word] = t
        # Merge word_index into main index as lower-priority fallback
        for word, rec in word_index.items():
            if word not in index:
                index[word] = rec
        return index
    except Exception:
        return {}

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
    sdi_index = load_sdi_index()
    
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
    files = [f for f in all_files if os.path.basename(f).replace('universal_predictions_','').replace('.json','') >= TRACKING_EPOCH]
    
    # stats[league_name][tier]
    stats = defaultdict(lambda: defaultdict(lambda: {
        'total': 0, 'wins_flat': 0, 'wins_5': 0, 'wins_10': 0, 'wins_15': 0, 'wins_20': 0,
        'ht_count': 0, 'ht_pct_sum': 0.0, 'ht_on_pace': 0
    }))
    
    search_lower = search_term.lower().strip()
    games_found = 0
    
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
            if search_lower in league_str or search_lower in home_str or search_lower in away_str:
                is_match = True
                
            if not is_match:
                continue
                
            exact_league_name = f"{p.get('country', '')} - {p.get('league', '')}".upper()
            
            # Track all team names seen for SDI lookup later
            if exact_league_name not in ["- "]:
                home_t = p.get('home_team', '')
                away_t = p.get('away_team', '')
                
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
            
            stats[exact_league_name][tier]['total'] += 1
            if actual_total >= model_total:
                stats[exact_league_name][tier]['wins_flat'] += 1
            if actual_total >= (model_total - 5):
                stats[exact_league_name][tier]['wins_5'] += 1
            if actual_total >= (model_total - 10):
                stats[exact_league_name][tier]['wins_10'] += 1
            if actual_total >= (model_total - 15):
                stats[exact_league_name][tier]['wins_15'] += 1
            if actual_total >= (model_total - 20):
                stats[exact_league_name][tier]['wins_20'] += 1

            # Halftime tracking (only if data was captured by grader)
            ht_pct = p.get('halftime_pct_of_model')
            if ht_pct is not None:
                stats[exact_league_name][tier]['ht_count'] += 1
                stats[exact_league_name][tier]['ht_pct_sum'] += ht_pct
                if ht_pct >= 50.0:  # on pace or ahead at halftime
                    stats[exact_league_name][tier]['ht_on_pace'] += 1
                
            games_found += 1
            
    # --- OUTPUT ---
    print("\n" + "="*80)
    print(f" SEARCH RESULTS FOR: '{search_term.upper()}'")
    print("="*80)
    
    if games_found == 0:
        print("\n  [X] No graded games found matching this search term since the tracking epoch.")
        print("  Check the spelling or try a broader search.\n")
        return

    # Collect all unique team names seen for SDI display
    all_team_names = set()
    for p_file in files:
        if not os.path.exists(p_file): continue
        with open(p_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for p in data.get('predictions', []):
            league_str = f"{p.get('country', '')} - {p.get('league', '')}".lower().replace('\u2014', '-')
            home_str = p.get('home_team', '').lower()
            away_str = p.get('away_team', '').lower()
            if search_lower in league_str or search_lower in home_str or search_lower in away_str:
                if p.get('home_team'): all_team_names.add(p.get('home_team'))
                if p.get('away_team'): all_team_names.add(p.get('away_team'))
        
    tier_names = {
        1: 'Tier 1 (Both Green)',
        2: 'Tier 2 (Both Colored)',
        3: 'Tier 3 (One Unstable)',
        4: 'Tier 4 (Both Unstable)'
    }
    
    for league_name, league_stats in sorted(stats.items()):
        # Check if any halftime data exists for this league
        has_ht = any(d.get('ht_count', 0) > 0 for d in league_stats.values())

        print(f"\n>> LEAGUE: {league_name}")
        header = (f'{"Stability Tier":<24} | {"Games":>5} | {"Flat Floor":>15}'
                  f' | {"-5 pts":>12} | {"-10 pts":>12} | {"-15 pts":>12} | {"-20 pts":>12}')
        if has_ht:
            header += f' | {"HT Pace":>10} | {"HT On-Pace":>11}'
        print(header)
        sep_width = 97 + (25 if has_ht else 0)
        print('-' * sep_width)
        
        total_games = 0
        total_flat = 0
        total_5 = 0
        total_10 = 0
        total_15 = 0
        total_20 = 0
        total_ht_count = 0
        total_ht_pct_sum = 0.0
        total_ht_on_pace = 0
        
        for t in range(1, 5):
            d = league_stats.get(t, {
                'total': 0, 'wins_flat': 0, 'wins_5': 0, 'wins_10': 0, 'wins_15': 0, 'wins_20': 0,
                'ht_count': 0, 'ht_pct_sum': 0.0, 'ht_on_pace': 0
            })
            tot = d['total']
            total_games += tot
            total_flat += d['wins_flat']
            total_5 += d['wins_5']
            total_10 += d['wins_10']
            total_15 += d.get('wins_15', 0)
            total_20 += d.get('wins_20', 0)
            total_ht_count += d.get('ht_count', 0)
            total_ht_pct_sum += d.get('ht_pct_sum', 0.0)
            total_ht_on_pace += d.get('ht_on_pace', 0)
            
            if tot == 0:
                row = (f'{tier_names[t]:<24} | {tot:>5} | {"-":>15}'
                       f' | {"-":>12} | {"-":>12} | {"-":>12} | {"-":>12}')
                if has_ht:
                    row += f' | {"-":>10} | {"-":>11}'
                print(row)
                continue
                
            pct_flat = (d['wins_flat'] / tot) * 100
            pct_5    = (d['wins_5']    / tot) * 100
            pct_10   = (d['wins_10']   / tot) * 100
            pct_15   = (d.get('wins_15', 0) / tot) * 100
            pct_20   = (d.get('wins_20', 0) / tot) * 100
            
            flat_str = f"{d['wins_flat']}/{tot} ({pct_flat:.0f}%)"
            str_5    = f"{d['wins_5']}/{tot} ({pct_5:.0f}%)"
            str_10   = f"{d['wins_10']}/{tot} ({pct_10:.0f}%)"
            str_15   = f"{d.get('wins_15',0)}/{tot} ({pct_15:.0f}%)"
            str_20   = f"{d.get('wins_20',0)}/{tot} ({pct_20:.0f}%)"
            
            row = (f'{tier_names[t]:<24} | {tot:>5} | {flat_str:>15}'
                   f' | {str_5:>12} | {str_10:>12} | {str_15:>12} | {str_20:>12}')

            if has_ht:
                ht_c = d.get('ht_count', 0)
                if ht_c > 0:
                    avg_ht = d['ht_pct_sum'] / ht_c
                    on_pace_pct = (d['ht_on_pace'] / ht_c) * 100
                    row += f' | {avg_ht:>9.1f}% | {d["ht_on_pace"]}/{ht_c} ({on_pace_pct:.0f}%)'
                else:
                    row += f' | {"-":>10} | {"-":>11}'
            print(row)
            
        print('-' * sep_width)
        
        # Print Totals
        if total_games > 0:
            pct_flat = (total_flat / total_games) * 100
            pct_5    = (total_5    / total_games) * 100
            pct_10   = (total_10   / total_games) * 100
            pct_15   = (total_15   / total_games) * 100
            pct_20   = (total_20   / total_games) * 100
            
            flat_str = f"{total_flat}/{total_games} ({pct_flat:.0f}%)"
            str_5    = f"{total_5}/{total_games} ({pct_5:.0f}%)"
            str_10   = f"{total_10}/{total_games} ({pct_10:.0f}%)"
            str_15   = f"{total_15}/{total_games} ({pct_15:.0f}%)"
            str_20   = f"{total_20}/{total_games} ({pct_20:.0f}%)"
            
            row = (f'{"OVERALL":<24} | {total_games:>5} | {flat_str:>15}'
                   f' | {str_5:>12} | {str_10:>12} | {str_15:>12} | {str_20:>12}')
            if has_ht and total_ht_count > 0:
                avg_ht_overall = total_ht_pct_sum / total_ht_count
                on_pace_overall = (total_ht_on_pace / total_ht_count) * 100
                row += f' | {avg_ht_overall:>9.1f}% | {total_ht_on_pace}/{total_ht_count} ({on_pace_overall:.0f}%)'
            print(row)
    
    # --- SDI SECTION ---
    if sdi_index:
        sdi_matches = []
        for team_name in all_team_names:
            t_lower = team_name.lower()
            rec = sdi_index.get(t_lower)
            if not rec and t_lower.split():
                words = t_lower.split()
                if t_lower.endswith(' w') or t_lower.endswith(' (w)'):
                    rec = sdi_index.get(words[0] + ' w')
                if not rec:
                    rec = sdi_index.get(words[0])
            
            if rec and rec not in sdi_matches:
                sdi_matches.append(rec)
        
        if sdi_matches:
            sdi_matches.sort(key=lambda x: x['avg_sdi'], reverse=True)
            print("\n" + "-"*70)
            print(" STAR DEPENDENCY INDEX (SDI) — Based on Proballers box score data")
            print("-"*70)
            print(f" {'Team':<35} {'SDI':>6} {'Top1':>5} {'Risk':<16} {'Key Stars'}")
            print(" " + "-"*90)
            for rec in sdi_matches:
                stars = ", ".join(
                    f"{p['name']} (top-2 in {p['times_top2']} games)"
                    for p in rec.get('top_players', [])[:2]
                )
                risk_col = rec['risk_label']
                print(f" {rec['team']:<35} {rec['avg_sdi']:>5}% {rec['avg_top1_pct']:>4}% {risk_col:<16} {stars}")
            print()
        else:
            if search_lower not in [''] and len(all_team_names) > 0:
                print("\n  [SDI] No player box-score data for this league in Proballers.")
                print("  SDI requires per-game player scoring — either this league has")
                print("  never been scraped, or was scraped before player data was captured.")
                print("  Fix: python scrape_proballers_batch.py  (then re-run calculate_sdi.py)\n")

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
