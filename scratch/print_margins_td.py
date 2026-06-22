import os
import re
import subprocess
import glob

reports = glob.glob('mlb/consensus_f5_v3_report_MLB_*.md')

date_files = {}
for report in reports:
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', report)
    if not date_match:
        continue
    date_str = date_match.group(1)
    if date_str not in date_files:
        date_files[date_str] = []
    date_files[date_str].append(report)

wins = []

for date_str in sorted(date_files.keys()):
    files = date_files[date_str]
    chosen_file = files[0]
    for f in files:
        if 'generic' not in f.lower():
            chosen_file = f
            break
            
    try:
        output = subprocess.check_output(
            ['python', 'mlb/grade_td_reports.py', '--file', chosen_file, '--date', date_str, '--td'], 
            universal_newlines=True, 
            stderr=subprocess.STDOUT
        )
        
        lines = output.split('\n')
        for i in range(len(lines)):
            if "Result" in lines[i] and "[WIN]" in lines[i]:
                game_line_str = lines[i-2].strip()
                action_str = lines[i-1].strip()
                result_str = lines[i].strip()
                
                m_line = re.search(r'\(Line: (.*?)\)', game_line_str)
                line_val = float(m_line.group(1)) if m_line else 4.5
                
                is_over = "OVER" in action_str
                
                m_runs = re.search(r'Result\s*:\s*(\d+\.?\d*)\s*runs', result_str)
                runs_val = float(m_runs.group(1)) if m_runs else 0
                
                if is_over:
                    margin = runs_val - line_val
                else:
                    margin = line_val - runs_val
                    
                matchup = game_line_str.split('(')[0].strip()
                
                wins.append({
                    'date': date_str,
                    'matchup': matchup,
                    'line': line_val,
                    'action': 'OVER' if is_over else 'UNDER',
                    'runs': runs_val,
                    'margin': margin
                })
    except Exception as e:
        pass

wins.sort(key=lambda x: x['margin'], reverse=True)

print("MARGINS_START")
total_margin = 0
for w in wins:
    margin_str = f"+{w['margin']}"
    print(f"| {w['date']} | {w['matchup']} | {w['action']} | {w['line']} | {w['runs']} | **{margin_str}** |")
    total_margin += w['margin']

avg_margin = total_margin / len(wins) if wins else 0
print(f"Total Wins: {len(wins)}")
print(f"Avg Margin: {avg_margin:.2f}")

flips = sum(1 for w in wins if w['margin'] == 0.5)
print(f"Flips: {flips}")

print("MARGINS_END")
