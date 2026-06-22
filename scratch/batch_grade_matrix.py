import os
import re
import subprocess
import glob

reports = glob.glob('mlb/consensus_f5_v3_report_MLB_*.md')
highest_wins = 0
highest_losses = 0

print("Grading Action Matrix (Highest Confidence) across all available MLB reports...\n")

results = []

for report in reports:
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', report)
    if not date_match:
        continue
    date_str = date_match.group(1)
    
    try:
        output = subprocess.check_output(['python', 'mlb/grade_td_reports.py', '--file', report, '--date', date_str, '--highest'], universal_newlines=True, stderr=subprocess.STDOUT)
        
        match = re.search(r'Matrix Summary -> Wins:\s+(\d+)\s+\|\s+Losses:\s+(\d+)', output)
        if match:
            w = int(match.group(1))
            l = int(match.group(2))
            highest_wins += w
            highest_losses += l
            filename = os.path.basename(report)
            results.append(f"{date_str} ({filename}): {w}-{l}")
            print(f"Processed {date_str} -> {w} Wins, {l} Losses")
    except Exception as e:
        print(f"Failed to process {report}: {e}")

print("\n" + "="*40)
print("ACTION MATRIX (HIGHEST CONFIDENCE) HISTORICAL RECORD")
print("="*40)
for r in results:
    print(r)
print("-" * 40)
print(f"TOTAL WINS  : {highest_wins}")
print(f"TOTAL LOSSES: {highest_losses}")
if (highest_wins + highest_losses) > 0:
    win_rate = highest_wins / (highest_wins + highest_losses) * 100
    print(f"WIN RATE    : {win_rate:.1f}%")
print("="*40)
