import sys
import os
import re
sys.path.insert(0, os.path.abspath('mlb'))
from grade_td_reports import find_game_id
import statsapi

files_to_grade = [
    ("mlb/consensus_f5_v3_report_MLB_2026-06-11.md", "2026-06-11"),
    ("mlb/consensus_f5_v3_report_MLB_2026-06-10.md", "2026-06-10"),
    ("mlb/consensus_f5_v3_report_MLB_2026-05-30.md", "2026-05-30"),
    ("mlb/consensus_f5_v3_report_MLB_2026-05-23.md", "2026-05-23"),
    ("mlb/consensus_f5_v3_report_MLB_2026-05-16.md", "2026-05-16"),
    ("mlb/consensus_f5_v3_report_MLB_2026-05-06.md", "2026-05-06")
]

line = 4.5

all_games = []

for filepath, date_str in files_to_grade:
    if not os.path.exists(filepath):
        continue
        
    schedule = statsapi.schedule(sportId=1, date=date_str)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = re.split(r'\n(?=###\s)', content.strip())
    for block in blocks:
        if not block.startswith('###'):
            continue
            
        # strip emojis manually to avoid regex errors
        clean_block = block.replace('??', '').replace('??', '').replace('???', '').replace('???', '').replace('??', '')
        
        header_match = re.match(r'###\s*(.*)', clean_block)
        if not header_match: continue
        raw_header = header_match.group(1).strip()
        matchup = re.sub(r'\s*\([^)]*\)', '', raw_header).strip()
        
        td_match = re.search(r'-\s*\*\*Top-Down Projected F5 Total:\*\*\s*(\d+\.?\d*)', clean_block)
        mc_match = re.search(r'-\s*\*\*Monte Carlo Simulated F5 Total:\*\*\s*(\d+\.?\d*)', clean_block)
        weather_match = re.search(r'Weather:\s*([+-]?\d+\.?\d*)%', clean_block)
        
        if not td_match or not mc_match: continue
        
        td_val = float(td_match.group(1))
        mc_val = float(mc_match.group(1))
        weather_val = float(weather_match.group(1)) if weather_match else 0.0
        
        gid = find_game_id(matchup, schedule)
        actual_total = None
        if gid:
            try:
                box = statsapi.get('game', {'gamePk': gid, 'hydrate': 'linescore'})
                innings = box.get('liveData', {}).get('linescore', {}).get('innings', [])
                if len(innings) >= 5:
                    a_runs = sum(inn.get('away', {}).get('runs', 0) for inn in innings[:5])
                    h_runs = sum(inn.get('home', {}).get('runs', 0) for inn in innings[:5])
                    actual_total = a_runs + h_runs
            except:
                pass
                
        if actual_total is not None:
            all_games.append({
                'matchup': matchup,
                'td': td_val,
                'mc': mc_val,
                'weather': weather_val,
                'actual': actual_total
            })

under_bets_by_weather = {'positive': {'w':0, 'l':0}, 'negative': {'w':0, 'l':0}}

td_wins = 0; td_losses = 0
mc_wins = 0; mc_losses = 0
agreed_wins = 0; agreed_losses = 0
disagreed_wins = 0; disagreed_losses = 0 # accuracy when they disagree (grading TD)

for g in all_games:
    td_bet = 'OVER' if g['td'] > line else 'UNDER'
    mc_bet = 'OVER' if g['mc'] > line else 'UNDER'
    actual_res = 'OVER' if g['actual'] > line else ('UNDER' if g['actual'] < line else 'PUSH')
    
    if actual_res == 'PUSH': continue
    
    if td_bet == 'UNDER':
        cat = 'positive' if g['weather'] > 0 else 'negative'
        if actual_res == 'UNDER': under_bets_by_weather[cat]['w'] += 1
        else: under_bets_by_weather[cat]['l'] += 1
        
    if td_bet == actual_res: td_wins += 1
    else: td_losses += 1
    
    if mc_bet == actual_res: mc_wins += 1
    else: mc_losses += 1
    
    if td_bet == mc_bet:
        if td_bet == actual_res: agreed_wins += 1
        else: agreed_losses += 1
    else:
        if td_bet == actual_res: disagreed_wins += 1
        else: disagreed_losses += 1

print("\n--- 1. WEATHER EFFECT ON TD UNDER PREDICTIONS ---")
pos_w = under_bets_by_weather['positive']['w']
pos_l = under_bets_by_weather['positive']['l']
neg_w = under_bets_by_weather['negative']['w']
neg_l = under_bets_by_weather['negative']['l']

print(f"When Weather was POSITIVE (+%):")
print(f"  Wins: {pos_w}, Losses: {pos_l} -> Win Rate: {pos_w/(pos_w+pos_l)*100 if pos_w+pos_l>0 else 0:.1f}%")
print(f"When Weather was NEGATIVE (-%):")
print(f"  Wins: {neg_w}, Losses: {neg_l} -> Win Rate: {neg_w/(neg_w+neg_l)*100 if neg_w+neg_l>0 else 0:.1f}%")

print("\n--- 2. TOP-DOWN vs MONTE CARLO ACCURACY ---")
print(f"Top-Down Accuracy: {td_wins/(td_wins+td_losses)*100:.1f}% ({td_wins}-{td_losses})")
print(f"Monte Carlo Accuracy: {mc_wins/(mc_wins+mc_losses)*100:.1f}% ({mc_wins}-{mc_losses})")

print("\n--- 3. AGREEMENT vs DISAGREEMENT ---")
print(f"When TD and MC AGREE: {agreed_wins/(agreed_wins+agreed_losses)*100:.1f}% ({agreed_wins}-{agreed_losses})")
if disagreed_wins+disagreed_losses > 0:
    print(f"When TD and MC DISAGREE (Grading TD): {disagreed_wins/(disagreed_wins+disagreed_losses)*100:.1f}% ({disagreed_wins}-{disagreed_losses})")
else:
    print("No Disagreements found.")
