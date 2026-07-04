import os
import re
import sys
import argparse
import requests
from datetime import datetime, timedelta

# ANSI Colors
C_GREEN = '\033[92m'
C_RED = '\033[91m'
C_YELLOW = '\033[93m'
C_RESET = '\033[0m'

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPORT_DIR = os.path.join(_BASE_DIR, '..', 'data', 'tennis')

def get_report_filepath(tour, date_str):
    filename = f"tennis_{tour.lower()}_report_{date_str}.md"
    return os.path.join(_REPORT_DIR, filename)

def parse_report(filepath):
    """
    Parses a tennis markdown report to extract bets.
    Returns:
    [
      {
        'matchup': 'Player A vs Player B',
        'p1': 'Player A',
        'p2': 'Player B',
        'bets': [
           {'market': 'Over 37.5 Games', 'line': 37.5, 'type': 'O/U', 'side': 'OVER', 'odds': 1.47},
           {'market': 'P1 Match Winner', 'type': 'ML', 'side': 'P1', 'odds': 1.66},
           {'market': 'P2 First Set Winner', 'type': 'FS', 'side': 'P2', 'odds': 1.5}
        ]
      }
    ]
    """
    if not os.path.exists(filepath):
        return []
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    games = []
    blocks = re.split(r'\n(?=###\s)', content.strip())
    
    for block in blocks:
        if '🎯 EDGE DETECTED' not in block:
            continue
            
        header_match = re.search(r'###\s+(.*?)\s+🎯 EDGE DETECTED', block)
        if not header_match:
            continue
            
        matchup = header_match.group(1).strip()
        parts = matchup.split(' vs ')
        if len(parts) != 2:
            continue
        p1, p2 = parts[0].strip(), parts[1].strip()
        
        bets = []
        
        # Check if Total Games is voided by retirement
        total_voided = '⚠️ **Total Games O/U voided**' in block
        
        edge_section = block.split('**EDGE ANALYSIS**')[-1]
        for line in edge_section.split('\n'):
            line = line.strip()
            if not line.startswith('- **'):
                continue
                
            market_match = re.search(r'-\s*\*\*(.*?)\*\*', line)
            if not market_match:
                continue
            market = market_match.group(1).strip()
            
            if 'Games' in market and not total_voided:
                # "Over 22.5 Games" or "Under 37.5 Games"
                m_parts = market.split()
                side = m_parts[0].upper()
                try:
                    total_line = float(m_parts[1])
                    bets.append({'market': market, 'type': 'O/U', 'side': side, 'line': total_line})
                except:
                    pass
            elif 'Match Winner' in market:
                # "P1 Match Winner" or "P2 Match Winner"
                side = 'P1' if 'P1' in market else 'P2'
                bets.append({'market': market, 'type': 'ML', 'side': side})
            elif 'First Set Winner' in market:
                side = 'P1' if 'P1' in market else 'P2'
                bets.append({'market': market, 'type': 'FS', 'side': side})
                
        if bets:
            games.append({
                'matchup': matchup,
                'p1': p1,
                'p2': p2,
                'bets': bets
            })
            
    return games

def fetch_espn_results(date_str, tour):
    """
    Fetch completed matches for the given date (YYYYMMDD).
    Returns dict mapping 'Player A vs Player B' (and reverse) -> result_data
    """
    league = 'atp' if tour == 'ATP' else 'wta'
    url = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{league}/scoreboard?dates={date_str}"
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[ESPN] Failed to fetch {tour} scoreboard: {e}")
        return {}
        
    target_slug = 'mens-singles' if tour == 'ATP' else 'womens-singles'
    results = {}
    
    for event in data.get('events', []):
        for grouping_block in event.get('groupings', []):
            if grouping_block.get('grouping', {}).get('slug') != target_slug:
                continue
                
            for comp in grouping_block.get('competitions', []):
                status_name = comp.get('status', {}).get('type', {}).get('name', '')
                if status_name not in ['STATUS_FINAL', 'STATUS_POSTPONED', 'STATUS_CANCELED']:
                    continue
                    
                competitors = sorted(comp.get('competitors', []), key=lambda x: x.get('order', 99))
                if len(competitors) < 2:
                    continue
                    
                p1_data = competitors[0]
                p2_data = competitors[1]
                p1_name = p1_data.get('athlete', {}).get('displayName', 'Unknown')
                p2_name = p2_data.get('athlete', {}).get('displayName', 'Unknown')
                
                linescores1 = p1_data.get('linescores', [])
                linescores2 = p2_data.get('linescores', [])
                
                if not linescores1 or not linescores2:
                    continue
                    
                p1_games = sum(s.get('value', 0) for s in linescores1)
                p2_games = sum(s.get('value', 0) for s in linescores2)
                total_games = p1_games + p2_games
                
                p1_won_match = p1_data.get('winner', False)
                p2_won_match = p2_data.get('winner', False)
                
                p1_won_fs = linescores1[0].get('winner', False) if linescores1 else False
                p2_won_fs = linescores2[0].get('winner', False) if linescores2 else False
                
                if not p1_won_fs and not p2_won_fs and linescores1 and linescores2:
                    if linescores1[0].get('value', 0) > linescores2[0].get('value', 0):
                        p1_won_fs = True
                    elif linescores2[0].get('value', 0) > linescores1[0].get('value', 0):
                        p2_won_fs = True
                
                res = {
                    'total_games': total_games,
                    'p1_won_match': p1_won_match,
                    'p2_won_match': p2_won_match,
                    'p1_won_fs': p1_won_fs,
                    'p2_won_fs': p2_won_fs,
                    'status': status_name
                }
                
                results[f"{p1_name} vs {p2_name}"] = res
                
                res_rev = {
                    'total_games': total_games,
                    'p1_won_match': p2_won_match,
                    'p2_won_match': p1_won_match,
                    'p1_won_fs': p2_won_fs,
                    'p2_won_fs': p1_won_fs,
                    'status': status_name
                }
                results[f"{p2_name} vs {p1_name}"] = res_rev
                
    return results

def grade_tour(tour, report_date_str, espn_date_str):
    filepath = get_report_filepath(tour, report_date_str)
    if not os.path.exists(filepath):
        print(f"[{tour}] No report found for {report_date_str}")
        return 0, 0, 0
        
    predicted_games = parse_report(filepath)
    if not predicted_games:
        print(f"[{tour}] No edges found in report for {report_date_str}")
        return 0, 0, 0
        
    results = fetch_espn_results(espn_date_str, tour)
    
    print(f"\n{'='*50}\n  {tour} GRADING REPORT - {report_date_str}\n{'='*50}")
    
    w_count = 0
    l_count = 0
    p_count = 0
    
    for game in predicted_games:
        matchup = game['matchup']
        bets = game['bets']
        
        res = results.get(matchup)
        
        if not res:
            print(f"\n  {matchup}")
            print(f"    [PENDING/NOT FOUND in ESPN final results]")
            continue
            
        print(f"\n  {matchup}")
        print(f"    Result: {res['total_games']} Total Games played.")
        
        for bet in bets:
            grade = "PENDING"
            market = bet['market']
            
            if bet['type'] == 'O/U':
                total_played = res['total_games']
                line = bet['line']
                if bet['side'] == 'OVER':
                    if total_played > line: grade = 'WIN'
                    elif total_played < line: grade = 'LOSS'
                    else: grade = 'PUSH'
                else:
                    if total_played < line: grade = 'WIN'
                    elif total_played > line: grade = 'LOSS'
                    else: grade = 'PUSH'
                    
            elif bet['type'] == 'ML':
                if bet['side'] == 'P1':
                    if res['p1_won_match']: grade = 'WIN'
                    else: grade = 'LOSS'
                else:
                    if res['p2_won_match']: grade = 'WIN'
                    else: grade = 'LOSS'
                    
            elif bet['type'] == 'FS':
                if bet['side'] == 'P1':
                    if res['p1_won_fs']: grade = 'WIN'
                    else: grade = 'LOSS'
                else:
                    if res['p2_won_fs']: grade = 'WIN'
                    else: grade = 'LOSS'
                    
            if grade == 'WIN':
                w_count += 1
                color = C_GREEN
            elif grade == 'LOSS':
                l_count += 1
                color = C_RED
            elif grade == 'PUSH':
                p_count += 1
                color = C_YELLOW
            else:
                color = C_RESET
                
            print(f"    {color}[{grade}]{C_RESET} {market}")
            
    return w_count, l_count, p_count

def main():
    parser = argparse.ArgumentParser(description="Grade Tennis Predictions")
    parser.add_argument('--date', type=str, default='', help='Date to grade (YYYY-MM-DD)')
    parser.add_argument('--tour', type=str, default='ALL', choices=['ATP', 'WTA', 'ALL', 'BOTH'], help='Tour to grade')
    args = parser.parse_args()
    
    if args.date:
        report_date = args.date
    else:
        report_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
    espn_date = report_date.replace('-', '')
    
    tours = ['ATP', 'WTA'] if args.tour in ['ALL', 'BOTH'] else [args.tour]
    
    total_w, total_l, total_p = 0, 0, 0
    for t in tours:
        w, l, p = grade_tour(t, report_date, espn_date)
        total_w += w
        total_l += l
        total_p += p
        
    print(f"\n{'='*50}")
    print(f"  TOTAL COMBINED RECORD: {total_w}-{total_l}-{total_p}")
    
    if (total_w + total_l) > 0:
        win_rate = total_w / (total_w + total_l) * 100
        print(f"  WIN RATE: {win_rate:.1f}%")
        units = total_w - (total_l * 1.1)
        color = C_GREEN if units > 0 else C_RED
        print(f"  NET UNITS (Assuming flat 1U @ -110): {color}{units:+.2f}U{C_RESET}")
    print(f"{'='*50}\n")

if __name__ == '__main__':
    main()
