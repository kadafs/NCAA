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
        output = subprocess.check_output(
            ['python', 'mlb/grade_td_reports.py', '--file', chosen_file, '--date', date_str, '--td'],
            universal_newlines=True,
            stderr=subprocess.STDOUT,
            encoding='utf-8'
        )

        lines = output.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if 'Result  :' not in line:
                continue
            if '[WIN]' not in line and '[LOSS]' not in line:
                continue

            game_line_str = lines[i-2].strip() if i >= 2 else ''
            action_str    = lines[i-1].strip() if i >= 1 else ''
            result_str    = line

            matchup_match = re.match(r'^(.*?)\s*\(Line:', game_line_str)
            matchup = matchup_match.group(1).strip() if matchup_match else game_line_str

            m_td = re.search(r'\(TD:\s*([\d.]+)\)', action_str)
            td_projection = float(m_td.group(1)) if m_td else None

            if 'Bet **OVER**' in action_str:
                bet_dir = 'OVER'
            elif 'Bet **UNDER**' in action_str:
                bet_dir = 'UNDER'
            else:
                bet_dir = None

            if bet_dir is None or td_projection is None:
                continue

            m_runs = re.search(r'Result\s*:\s*([\d.]+)\s*runs', result_str)
            actual_runs = float(m_runs.group(1)) if m_runs else None
            if actual_runs is None:
                continue

            outcome = 'WIN' if '[WIN]' in result_str else 'LOSS'
            error = round(td_projection - actual_runs, 2)

            results.append({
                'date': date_str,
                'matchup': matchup,
                'td_projection': td_projection,
                'bet_dir': bet_dir,
                'actual_runs': actual_runs,
                'error': error,
                'abs_error': abs(error),
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
    losses = total - wins
    avg_td = sum(r['td_projection'] for r in group) / total
    avg_actual = sum(r['actual_runs'] for r in group) / total
    avg_error = sum(r['error'] for r in group) / total
    avg_abs   = sum(r['abs_error'] for r in group) / total
    within_1  = sum(1 for r in group if r['abs_error'] <= 1.0)
    within_2  = sum(1 for r in group if r['abs_error'] <= 2.0)
    over_pred = sum(1 for r in group if r['error'] > 0)
    under_pred= sum(1 for r in group if r['error'] < 0)

    print(f"\n{'='*60}")
    print(f"  {label} BETS  ({total} games)")
    print(f"{'='*60}")
    print(f"  Record         : {wins}-{losses} ({wins/total*100:.1f}%)")
    print(f"  Avg TD Proj    : {avg_td:.2f} runs")
    print(f"  Avg Actual F5  : {avg_actual:.2f} runs")
    print(f"  Mean Bias      : {avg_error:+.2f} runs")
    print(f"  Mean Abs Error : {avg_abs:.2f} runs")
    print(f"  Within 1.0 run : {within_1}/{total} ({within_1/total*100:.1f}%)")
    print(f"  Within 2.0 runs: {within_2}/{total} ({within_2/total*100:.1f}%)")
    print(f"  Over-predicted : {over_pred} games")
    print(f"  Under-predicted: {under_pred} games")

    # Wins vs Losses breakdown
    win_group  = [r for r in group if r['outcome'] == 'WIN']
    loss_group = [r for r in group if r['outcome'] == 'LOSS']

    if win_group:
        w_avg_actual = sum(r['actual_runs'] for r in win_group) / len(win_group)
        w_avg_err    = sum(r['abs_error'] for r in win_group) / len(win_group)
        print(f"\n  --- WINs ({len(win_group)}) ---")
        print(f"  Avg Actual F5  : {w_avg_actual:.2f} runs")
        print(f"  Avg Abs Error  : {w_avg_err:.2f} runs")

    if loss_group:
        l_avg_actual = sum(r['actual_runs'] for r in loss_group) / len(loss_group)
        l_avg_err    = sum(r['abs_error'] for r in loss_group) / len(loss_group)
        print(f"\n  --- LOSSes ({len(loss_group)}) ---")
        print(f"  Avg Actual F5  : {l_avg_actual:.2f} runs")
        print(f"  Avg Abs Error  : {l_avg_err:.2f} runs")

    # Game-by-game list
    sorted_group = sorted(group, key=lambda x: (x['date'], x['matchup']))
    print(f"\n  {'Date':<12} {'Matchup':<42} {'TD Proj':<9} {'Actual':<9} {'Error':<9} {'Result'}")
    print(f"  {'-'*104}")
    for r in sorted_group:
        err_str = f"{r['error']:+.2f}"
        print(f"  {r['date']:<12} {r['matchup']:<42} {r['td_projection']:<9} {r['actual_runs']:<9} {err_str:<9} {r['outcome']}")

stats(overs,  "OVER")
stats(unders, "UNDER")

print(f"\n\nOVERALL: {len(results)} games | {sum(1 for r in results if r['outcome']=='WIN')}-{sum(1 for r in results if r['outcome']=='LOSS')}")
