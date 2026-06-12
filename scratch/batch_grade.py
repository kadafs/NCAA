import sys
import os
sys.path.insert(0, os.path.abspath('mlb'))
from grade_td_reports import parse_report, find_game_id
import statsapi

files_to_grade = [
    ("mlb/consensus_f5_v3_report_MLB_2026-06-11.md", "2026-06-11"),
    ("mlb/consensus_f5_v3_report_MLB_2026-06-10.md", "2026-06-10"),
    ("mlb/consensus_f5_v3_report_MLB_2026-05-30.md", "2026-05-30"),
    ("mlb/consensus_f5_v3_report_MLB_2026-05-23.md", "2026-05-23"),
    ("mlb/consensus_f5_v3_report_MLB_2026-05-16.md", "2026-05-16"),
    ("mlb/consensus_f5_v3_report_MLB_2026-05-06.md", "2026-05-06")
]

over_wins = 0
over_losses = 0
over_pushes = 0
under_wins = 0
under_losses = 0
under_pushes = 0

line = 4.5

for filepath, date_str in files_to_grade:
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (Not Found)")
        continue
        
    schedule = statsapi.schedule(sportId=1, date=date_str)
    games = parse_report(filepath, line=line)
    
    for g in games:
        gid = find_game_id(g['matchup'], schedule)
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
            if actual_total < line:
                actual_result = "UNDER"
            elif actual_total > line:
                actual_result = "OVER"
            else:
                actual_result = "PUSH"
                
            if g['td_bet'] == "OVER":
                if actual_result == "OVER": over_wins += 1
                elif actual_result == "UNDER": over_losses += 1
                else: over_pushes += 1
            elif g['td_bet'] == "UNDER":
                if actual_result == "UNDER": under_wins += 1
                elif actual_result == "OVER": under_losses += 1
                else: under_pushes += 1

print("\n--- RESULTS OVER 6 DATES (Line: 4.5) ---")
print("OVERS:")
print(f"  Wins: {over_wins}")
print(f"  Losses: {over_losses}")
print(f"  Pushes: {over_pushes}")
if over_wins + over_losses > 0:
    print(f"  Win Rate: {over_wins / (over_wins + over_losses) * 100:.1f}%")

print("\nUNDERS:")
print(f"  Wins: {under_wins}")
print(f"  Losses: {under_losses}")
print(f"  Pushes: {under_pushes}")
if under_wins + under_losses > 0:
    print(f"  Win Rate: {under_wins / (under_wins + under_losses) * 100:.1f}%")
