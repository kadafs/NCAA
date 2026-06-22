import os
import re
import subprocess
import glob

# Get all reports
reports = glob.glob('mlb/consensus_f5_v3_report_MLB_*.md')

# Group by date
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
    # Prefer confirmed (the one WITHOUT generic in the name)
    chosen_file = files[0]
    for f in files:
        if 'generic' not in f.lower():
            chosen_file = f
            break
            
    try:
        output = subprocess.check_output(
            ['python', 'mlb/grade_td_reports.py', '--file', chosen_file, '--date', date_str], 
            universal_newlines=True, 
            stderr=subprocess.STDOUT
        )
        
        lines = output.split('\n')
        for i in range(len(lines)):
            if "Result" in lines[i] and "[WIN]" in lines[i]:
                # We found a win! Let's get context
                game_line_str = lines[i-2].strip()
                action_str = lines[i-1].strip()
                result_str = lines[i].strip()
                
                # Extract Line
                m_line = re.search(r'\(Line: (.*?)\)', game_line_str)
                line_val = float(m_line.group(1)) if m_line else 4.5
                
                # Extract Action (OVER/UNDER)
                is_over = "OVER" in action_str
                
                # Extract Runs
                m_runs = re.search(r'Result\s*:\s*(\d+\.?\d*)\s*runs', result_str)
                runs_val = float(m_runs.group(1)) if m_runs else 0
                
                # Calculate margin
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

# Generate Markdown
md = "# Default 4.5 Line (w/ Skips) Winning Margins\n\n"
md += "This table shows all historical wins using the Default 4.5 Action Matrix logic (which skips games lacking a high confidence edge).\n\n"
md += "| Date | Matchup | Action | Line | F5 Runs | Margin |\n"
md += "|------|---------|--------|------|---------|--------|\n"

# Sort by margin (highest first)
wins.sort(key=lambda x: x['margin'], reverse=True)

total_margin = 0
for w in wins:
    margin_str = f"+{w['margin']}"
    md += f"| {w['date']} | {w['matchup']} | {w['action']} | {w['line']} | {w['runs']} | **{margin_str}** |\n"
    total_margin += w['margin']

avg_margin = total_margin / len(wins) if wins else 0
md += f"\n**Total Wins Analyzed:** {len(wins)}\n"
md += f"**Average Winning Margin:** +{avg_margin:.2f} runs\n"

with open('scratch/margins.md', 'w') as f:
    f.write(md)
print(f"Generated margins.md with {len(wins)} wins.")
