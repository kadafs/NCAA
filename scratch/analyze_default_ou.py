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

results = []

for date_str in sorted(date_files.keys()):
    files = date_files[date_str]
    chosen_file = files[0]
    for f in files:
        if 'generic' not in f.lower():
            chosen_file = f
            break

    try:
        # Default fixed 4.5 grading
        output = subprocess.check_output(
            ['python', 'mlb/grade_td_reports.py', '--file', chosen_file, '--date', date_str],
            universal_newlines=True,
            stderr=subprocess.STDOUT,
            encoding='utf-8'
        )

        lines = output.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if 'Result  :' not in line:
                continue
            if '[WIN]' not in line and '[LOSS]' not in line and '[PUSH]' not in line:
                continue

            game_line_str = lines[i-2].strip() if i >= 2 else ''
            action_str    = lines[i-1].strip() if i >= 1 else ''
            result_str    = line

            matchup_match = re.match(r'^(.*?)\s*\(Line:', game_line_str)
            matchup = matchup_match.group(1).strip() if matchup_match else game_line_str

            m_gline = re.search(r'\(Line:\s*([\d.]+)\)', game_line_str)
            game_line = float(m_gline.group(1)) if m_gline else 4.5

            if 'Bet **OVER**' in action_str:
                bet_dir = 'OVER'
            elif 'Bet **UNDER**' in action_str:
                bet_dir = 'UNDER'
            else:
                continue  # Skip

            m_runs = re.search(r'Result\s*:\s*([\d.]+)\s*runs', result_str)
            actual_runs = float(m_runs.group(1)) if m_runs else None
            if actual_runs is None:
                continue

            if '[WIN]' in result_str:
                outcome = 'WIN'
            elif '[LOSS]' in result_str:
                outcome = 'LOSS'
            else:
                outcome = 'PUSH'

            if outcome == 'PUSH':
                continue # Ignore pushes for win rate

            if bet_dir == 'OVER':
                margin = actual_runs - game_line
            else:
                margin = game_line - actual_runs

            results.append({
                'date': date_str,
                'matchup': matchup,
                'bet_dir': bet_dir,
                'game_line': game_line,
                'actual_runs': actual_runs,
                'margin': margin,
                'outcome': outcome
            })

    except Exception as e:
        pass

overs  = [r for r in results if r['bet_dir'] == 'OVER']
unders = [r for r in results if r['bet_dir'] == 'UNDER']

def stats(group, label):
    total = len(group)
    if total == 0:
        return
    wins   = sum(1 for r in group if r['outcome'] == 'WIN')
    losses = sum(1 for r in group if r['outcome'] == 'LOSS')
    
    if (wins + losses) == 0:
        return

    win_rate = wins / (wins + losses) * 100
    avg_actual = sum(r['actual_runs'] for r in group) / total
    
    win_group  = [r for r in group if r['outcome'] == 'WIN']
    loss_group = [r for r in group if r['outcome'] == 'LOSS']

    print(f"\n{'='*60}")
    print(f"  {label} BETS  (Default Action Matrix at 4.5)")
    print(f"{'='*60}")
    print(f"  Total Bets     : {total}")
    print(f"  Record         : {wins}-{losses} ({win_rate:.1f}%)")
    print(f"  Avg Actual F5  : {avg_actual:.2f} runs")

    if win_group:
        w_avg_actual = sum(r['actual_runs'] for r in win_group) / len(win_group)
        w_avg_margin = sum(r['margin'] for r in win_group) / len(win_group)
        print(f"\n  --- WINs ({len(win_group)}) ---")
        print(f"  Avg Actual F5  : {w_avg_actual:.2f} runs")
        print(f"  Avg Win Margin : +{w_avg_margin:.2f} runs (distance from 4.5 line)")

    if loss_group:
        l_avg_actual = sum(r['actual_runs'] for r in loss_group) / len(loss_group)
        l_avg_margin = sum(r['margin'] for r in loss_group) / len(loss_group)
        print(f"\n  --- LOSSes ({len(loss_group)}) ---")
        print(f"  Avg Actual F5  : {l_avg_actual:.2f} runs")
        print(f"  Avg Loss Margin: {l_avg_margin:.2f} runs (distance from 4.5 line)")

stats(overs,  "OVER")
stats(unders, "UNDER")

wins = sum(1 for r in results if r['outcome'] == 'WIN')
losses = sum(1 for r in results if r['outcome'] == 'LOSS')
print(f"\n\nOVERALL DEFAULT MATRIX: {len(results)} bets | {wins}-{losses} ({(wins/(wins+losses)*100):.1f}%)")
