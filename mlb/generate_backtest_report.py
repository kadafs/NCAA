"""
generate_backtest_report.py
===========================
Reads the completed backtest log files and outputs a rich daily 
breakdown markdown report styled after grade_td_reports.py and consensus_f5_v3.py.

Usage:
    python mlb/generate_backtest_report.py
    python mlb/generate_backtest_report.py --file mlb/backtest_clean.log
    python mlb/generate_backtest_report.py --confidence HIGH
    python mlb/generate_backtest_report.py --confidence MODERATE
"""

import re
import argparse
import os
from datetime import datetime

LINE = 4.5
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def parse_logs(*filenames):
    """Parse one or more backtest log files into daily buckets."""
    days = {}
    
    for filename in filenames:
        if not os.path.exists(filename):
            continue
        try:
            with open(filename, 'r', encoding='utf-16') as f:
                text = f.read()
        except UnicodeError:
            with open(filename, 'r', encoding='utf-8') as f:
                text = f.read()
        
        for day_block in text.split('Backtesting Date: ')[1:]:
            date_str = day_block.split('\n')[0].strip()
            if date_str not in days:
                days[date_str] = []
            
            for game_block in day_block.split('Processing: ')[1:]:
                try:
                    matchup = game_block.split('\n')[0].strip()
                    td = float(re.search(r'TD: ([\-\d\.]+)', game_block).group(1))
                    mc = float(re.search(r'MC Under 4\.5 Prob: ([\d\.]+)', game_block).group(1))
                    sig_m = re.search(r'-> Signal: ([A-Z]+) \(([A-Z\-]+)\)', game_block)
                    signal = sig_m.group(1)
                    conf = sig_m.group(2)
                    runs_str = re.search(r'Actual F5 Runs: ([\d]+|None)', game_block).group(1)
                    actual = int(runs_str) if runs_str != 'None' else None
                    grade = re.search(r'Grade: ([A-Z]+)', game_block).group(1)
                    
                    days[date_str].append({
                        'matchup': matchup,
                        'td': td,
                        'mc': mc,
                        'signal': signal,
                        'conf': conf,
                        'actual': actual,
                        'grade': grade,
                    })
                except Exception:
                    pass
    
    return dict(sorted(days.items()))


def build_markdown(days, confidence_filter=None):
    """Build a markdown report string from parsed day data."""
    conf_label = confidence_filter if confidence_filter else "HIGH + MODERATE"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = []
    lines.append(f"# Backtest Report — {conf_label} Confidence")
    lines.append(f"**Generated:** {generated_at} | **Line:** {LINE} Runs | **Confidence Filter:** {conf_label}")
    lines.append("")
    lines.append("---")
    lines.append("")

    total_w = total_l = 0
    total_units = 0.0
    day_summaries = []

    # --- Per-Day Sections ---
    for date_str, games in days.items():
        day_w = day_l = 0
        day_units = 0.0
        game_rows = []

        for g in games:
            if g['signal'] == 'SKIP' or g['grade'] == 'PENDING':
                continue
            if confidence_filter and g['conf'] != confidence_filter:
                continue

            grade = g['grade']
            if grade == 'WIN':
                day_w += 1
                day_units += 1
            elif grade == 'LOSS':
                day_l += 1
                day_units -= 1

            td_gap = g['td'] - LINE
            td_arrow = f"+{td_gap:.2f}" if td_gap > 0 else f"{td_gap:.2f}"
            mc_pct = int(g['mc'] * 100)

            actual_str = f"{g['actual']} runs" if g['actual'] is not None else "N/A"
            if g['actual'] is not None:
                actual_dir = "OVER" if g['actual'] > LINE else ("UNDER" if g['actual'] < LINE else "PUSH")
                actual_str += f" ({actual_dir})"

            if grade == 'WIN':
                grade_badge = "**WIN**"
            elif grade == 'LOSS':
                grade_badge = "~~LOSS~~"
            else:
                grade_badge = "PENDING"

            game_rows.append((g, grade_badge, td_arrow, mc_pct, actual_str, day_units))

        if not game_rows:
            continue

        total_w += day_w
        total_l += day_l
        total_units += day_units
        day_total = day_w + day_l
        day_pct = (day_w / day_total * 100) if day_total > 0 else 0.0

        lines.append(f"## {date_str} — {day_w}W / {day_l}L ({day_pct:.0f}%) | {day_units:+.1f} units")
        lines.append("")
        lines.append("| Result | Matchup | Signal | TD | TD Gap | MC% Under | Actual |")
        lines.append("|--------|---------|--------|----|--------|-----------|--------|")

        for (g, grade_badge, td_arrow, mc_pct, actual_str, _) in game_rows:
            signal_conf = f"{g['signal']} ({g['conf']})"
            lines.append(f"| {grade_badge} | {g['matchup']} | {signal_conf} | {g['td']:.2f} | {td_arrow} | {mc_pct}% | {actual_str} |")

        lines.append("")
        day_summaries.append((date_str, day_w, day_l, day_pct, day_units))

    # --- Summary Table ---
    overall_pct = (total_w / (total_w + total_l) * 100) if (total_w + total_l) > 0 else 0.0
    lines.append("---")
    lines.append("")
    lines.append(f"## Daily Summary Table — {conf_label}")
    lines.append("")
    lines.append("| Date | W | L | Win% | Net Units | Running Total |")
    lines.append("|------|---|---|------|-----------|---------------|")

    running = 0.0
    for (date_str, w, l, pct, units) in day_summaries:
        running += units
        lines.append(f"| {date_str} | {w} | {l} | {pct:.0f}% | {units:+.1f}u | {running:+.1f}u |")

    lines.append(f"| **TOTAL** | **{total_w}** | **{total_l}** | **{overall_pct:.1f}%** | **{total_units:+.1f}u** | |")
    lines.append("")
    lines.append("---")
    lines.append(f"*Backtest F5 system | Line: {LINE} | Filter: {conf_label}*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate a markdown backtest report')
    parser.add_argument('--file', type=str, default='backtest_f5.log', help="The log file to parse")
    parser.add_argument('--confidence', type=str, choices=['HIGH', 'MODERATE', 'TD-ONLY'], default=None,
                        help="Filter to only include games with this confidence tier")
    args = parser.parse_args()

    if args.file:
        files = [args.file]
    else:
        files = [
            os.path.join(SCRIPT_DIR, 'final_backtest_results.log'),
            os.path.join(SCRIPT_DIR, 'backtest_results_may_june.log'),
        ]

    days = parse_logs(*files)

    md = build_markdown(days, confidence_filter=args.confidence)

    conf_suffix = f"_{args.confidence}" if args.confidence else "_ALL"
    out_filename = f"backtest_report{conf_suffix}.md"
    out_path = os.path.join(SCRIPT_DIR, out_filename)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"Report written to: {out_path}")

    # Quick terminal summary
    days_data = parse_logs(*files)
    total_w = total_l = 0
    for g_list in days_data.values():
        for g in g_list:
            if g['signal'] == 'SKIP': continue
            if args.confidence and g['conf'] != args.confidence: continue
            if g['grade'] == 'WIN': total_w += 1
            elif g['grade'] == 'LOSS': total_l += 1

    pct = (total_w / (total_w + total_l) * 100) if (total_w + total_l) > 0 else 0
    print(f"Summary: {total_w}W - {total_l}L ({pct:.1f}%) | {total_w - total_l:+d} units")


if __name__ == '__main__':
    main()
