import os
import re
import subprocess
import glob

reports = glob.glob('mlb/consensus_f5_v3_report_MLB_*.md')
highest_wins = 0
highest_losses = 0

print("Grading Action Matrix (--highest) across deduplicated MLB reports...\n")

date_files = {}
for report in reports:
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', report)
    if not date_match:
        continue
    date_str = date_match.group(1)
    if date_str not in date_files:
        date_files[date_str] = []
    date_files[date_str].append(report)

results = []

for date_str in sorted(date_files.keys()):
    files = date_files[date_str]
    chosen_file = files[0]
    for f in files:
        if 'generic' not in f.lower():
            chosen_file = f
            break
            
    try:
        output = subprocess.check_output(
            ['python', 'mlb/grade_td_reports.py', '--file', chosen_file, '--date', date_str, '--highest'], 
            universal_newlines=True, 
            stderr=subprocess.STDOUT
        )
        
        match = re.search(r'Matrix Summary -> Wins:\s+(\d+)\s+\|\s+Losses:\s+(\d+)', output)
        if match:
            w = int(match.group(1))
            l = int(match.group(2))
            highest_wins += w
            highest_losses += l
            filename = os.path.basename(chosen_file)
            results.append(f"{date_str} ({filename}): {w}-{l}")
            print(f"Processed {date_str} -> {w} Wins, {l} Losses")
    except Exception as e:
        pass

print("\n" + "="*50)
print("ACTION MATRIX (--highest) HISTORICAL RECORD (DEDUPLICATED)")
print("="*50)
for r in results:
    print(r)
print("-" * 50)
print(f"TOTAL WINS  : {highest_wins}")
print(f"TOTAL LOSSES: {highest_losses}")
if (highest_wins + highest_losses) > 0:
    win_rate = highest_wins / (highest_wins + highest_losses) * 100
    print(f"WIN RATE    : {win_rate:.1f}%")
print("="*50)
