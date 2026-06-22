import os
import re
import subprocess
import glob

# Get all reports, deduplicate by date
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
    # Prefer confirmed file over generic
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

            # The grader prints:
            # Line i-2:  {matchup} (Line: {game_line})
            # Line i-1:  Action  : Bet **OVER** (TD: 4.72)
            # Line i:    Result  : X runs (F5 OVER/UNDER)  |  [WIN/LOSS]

            if 'Result  :' not in line:
                continue
            if '[WIN]' not in line and '[LOSS]' not in line:
                continue

            game_line_str = lines[i-2].strip() if i >= 2 else ''
            action_str    = lines[i-1].strip() if i >= 1 else ''
            result_str    = line

            # Extract matchup
            matchup_match = re.match(r'^(.*?)\s*\(Line:', game_line_str)
            matchup = matchup_match.group(1).strip() if matchup_match else game_line_str

            # Extract game line
            m_gline = re.search(r'\(Line: ([\d.]+)\)', game_line_str)
            game_line = float(m_gline.group(1)) if m_gline else 4.5

            # Extract TD projection from action string (TD: X.XX)
            m_td = re.search(r'\(TD:\s*([\d.]+)\)', action_str)
            td_projection = float(m_td.group(1)) if m_td else None

            # Extract bet direction
            is_over = 'OVER' in action_str and 'UNDER' not in action_str.split('OVER')[0]
            # More reliable: check for explicit Bet **OVER** or Bet **UNDER**
            if 'Bet **OVER**' in action_str:
                bet_dir = 'OVER'
            elif 'Bet **UNDER**' in action_str:
                bet_dir = 'UNDER'
            else:
                bet_dir = 'OVER' if is_over else 'UNDER'

            # Extract actual F5 runs from result line
            m_runs = re.search(r'Result\s*:\s*([\d.]+)\s*runs', result_str)
            actual_runs = float(m_runs.group(1)) if m_runs else None
            if actual_runs is None:
                continue

            outcome = 'WIN' if '[WIN]' in result_str else 'LOSS'

            # Calculate the error: projected vs actual
            error = round(td_projection - actual_runs, 2) if td_projection is not None else None
            abs_error = abs(error) if error is not None else None

            results.append({
                'date': date_str,
                'matchup': matchup,
                'td_projection': td_projection,
                'bet_dir': bet_dir,
                'game_line': game_line,
                'actual_runs': actual_runs,
                'error': error,
                'abs_error': abs_error,
                'outcome': outcome
            })

    except Exception as e:
        print(f"Failed {chosen_file}: {e}")

# Filter out entries missing TD projection
valid = [r for r in results if r['td_projection'] is not None]

total = len(valid)
avg_error = sum(r['error'] for r in valid) / total if total else 0
avg_abs_error = sum(r['abs_error'] for r in valid) / total if total else 0
within_1   = sum(1 for r in valid if r['abs_error'] <= 1.0)
within_1_5 = sum(1 for r in valid if r['abs_error'] <= 1.5)
within_2   = sum(1 for r in valid if r['abs_error'] <= 2.0)
over_pred  = sum(1 for r in valid if r['error'] > 0)
under_pred = sum(1 for r in valid if r['error'] < 0)
exact      = sum(1 for r in valid if r['error'] == 0)

wins_list  = [r for r in valid if r['outcome'] == 'WIN']
losses_list= [r for r in valid if r['outcome'] == 'LOSS']

print(f"\n{'='*60}")
print(f"TD PROJECTION vs ACTUAL F5 SCORELINE (Corrected)")
print(f"{'='*60}")
print(f"Games Analyzed    : {total} ({len(wins_list)} Wins, {len(losses_list)} Losses)")
print(f"Mean Error (bias) : {avg_error:+.2f} runs (+ = over-predicted)")
print(f"Mean Abs Error    : {avg_abs_error:.2f} runs")
print(f"Within 1.0 run    : {within_1}/{total} ({within_1/total*100:.1f}%)")
print(f"Within 1.5 runs   : {within_1_5}/{total} ({within_1_5/total*100:.1f}%)")
print(f"Within 2.0 runs   : {within_2}/{total} ({within_2/total*100:.1f}%)")
print(f"Over-predicted    : {over_pred} games")
print(f"Under-predicted   : {under_pred} games")
print(f"Exact hit         : {exact} games")
print(f"{'='*60}\n")

# Show wins by margin category
win_abs_errors = [r['abs_error'] for r in wins_list]
loss_abs_errors = [r['abs_error'] for r in losses_list]
avg_win_margin  = sum(win_abs_errors)/len(win_abs_errors) if win_abs_errors else 0
avg_loss_margin = sum(loss_abs_errors)/len(loss_abs_errors) if loss_abs_errors else 0
print(f"Avg abs error on WINs : {avg_win_margin:.2f} runs")
print(f"Avg abs error on LOSSes: {avg_loss_margin:.2f} runs\n")

# Sort by absolute error
valid_sorted = sorted(valid, key=lambda x: x['abs_error'])

print("TOP 20 MOST ACCURATE PREDICTIONS:")
print(f"{'Date':<12} {'Matchup':<45} {'TD Proj':<9} {'Actual':<9} {'Error':<9} {'Bet':<7} {'Result'}")
print("-" * 110)
for r in valid_sorted[:20]:
    err_str = f"{r['error']:+.2f}"
    print(f"{r['date']:<12} {r['matchup']:<45} {r['td_projection']:<9} {r['actual_runs']:<9} {err_str:<9} {r['bet_dir']:<7} {r['outcome']}")

print()

valid_worst = sorted(valid, key=lambda x: x['abs_error'], reverse=True)
print("TOP 20 BIGGEST MISSES (sorted by absolute error):")
print(f"{'Date':<12} {'Matchup':<45} {'TD Proj':<9} {'Actual':<9} {'Error':<9} {'Bet':<7} {'Result'}")
print("-" * 110)
for r in valid_worst[:20]:
    err_str = f"{r['error']:+.2f}"
    print(f"{r['date']:<12} {r['matchup']:<45} {r['td_projection']:<9} {r['actual_runs']:<9} {err_str:<9} {r['bet_dir']:<7} {r['outcome']}")
