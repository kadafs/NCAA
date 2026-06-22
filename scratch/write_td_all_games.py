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
                bet_dir = '?'

            m_runs = re.search(r'Result\s*:\s*([\d.]+)\s*runs', result_str)
            actual_runs = float(m_runs.group(1)) if m_runs else None
            if actual_runs is None or td_projection is None:
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

# Sort by date then matchup
results_sorted = sorted(results, key=lambda x: (x['date'], x['matchup']))

# Build markdown artifact
artifact_path = r'C:\Users\markk\.gemini\antigravity-ide\brain\0ecf1e2e-0e8f-4e9d-870a-a7e5cfa6986d\td_vs_actual_all.md'

wins  = [r for r in results_sorted if r['outcome'] == 'WIN']
losses = [r for r in results_sorted if r['outcome'] == 'LOSS']

total = len(results_sorted)
avg_err = sum(r['error'] for r in results_sorted) / total
avg_abs = sum(r['abs_error'] for r in results_sorted) / total
under_pred = sum(1 for r in results_sorted if r['error'] < 0)
over_pred  = sum(1 for r in results_sorted if r['error'] > 0)

md = "# TD Projection vs Actual F5 Scoreline — All Games\n\n"
md += f"**{total} games** | **{len(wins)} Wins** | **{len(losses)} Losses** | Win Rate: **{len(wins)/total*100:.1f}%**\n\n"
md += f"Mean Bias: **{avg_err:+.2f} runs** (negative = model under-predicts) | Mean Abs Error: **{avg_abs:.2f} runs**\n\n"
md += f"Over-predicted: {over_pred} games | Under-predicted: {under_pred} games\n\n"
md += "---\n\n"

md += "| Date | Matchup | Bet | TD Proj | Actual F5 | Error | Result |\n"
md += "|------|---------|-----|---------|-----------|-------|--------|\n"

for r in results_sorted:
    err_str = f"{r['error']:+.2f}"
    result_emoji = "✅ WIN" if r['outcome'] == 'WIN' else "❌ LOSS"
    md += f"| {r['date']} | {r['matchup']} | {r['bet_dir']} | {r['td_projection']} | {r['actual_runs']} | {err_str} | {result_emoji} |\n"

with open(artifact_path, 'w', encoding='utf-8') as f:
    f.write(md)

print(f"Artifact written: {len(results_sorted)} games.")
