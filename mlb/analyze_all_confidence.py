import re

def analyze(filename, label):
    try:
        with open(filename, 'r', encoding='utf-16') as f:
            text = f.read()
    except UnicodeError:
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()

    days = text.split('Backtesting Date: ')[1:]
    
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  {'Date':<15} | {'W':<4} | {'L':<4} | {'Win%':<7} | {'Net':>5}")
    print(f"  {'-'*55}")
    
    total_w = total_l = 0
    total_units = 0.0

    for d in days:
        date_str = d.split('\n')[0].strip()
        games = d.split('Processing: ')[1:]
        wins = losses = 0
        for g in games:
            # HIGH + MODERATE — exclude SKIP
            if '(HIGH)' in g or '(MODERATE)' in g:
                if 'Grade: WIN' in g: wins += 1
                elif 'Grade: LOSS' in g: losses += 1
        total_w += wins
        total_l += losses
        day_units = wins - losses
        total_units += day_units
        total = wins + losses
        pct = (wins / total * 100) if total > 0 else 0
        print(f"  {date_str:<15} | {wins:<4} | {losses:<4} | {pct:>5.1f}%  | {day_units:>+5.1f}u")

    print(f"  {'='*55}")
    overall_pct = (total_w / (total_w + total_l) * 100) if (total_w + total_l) > 0 else 0
    print(f"  TOTAL (H+M): {total_w}-{total_l} ({overall_pct:.1f}%) | {total_units:+.1f} units")
    return total_w, total_l, total_units

r1_w, r1_l, r1_u = analyze('final_backtest_results.log', 'PERIOD 1: Apr 10 - May 10')
r2_w, r2_l, r2_u = analyze('backtest_results_may_june.log', 'PERIOD 2: May 11 - Jun 13')

total_w = r1_w + r2_w
total_l = r1_l + r2_l
total_u = r1_u + r2_u
pct = (total_w / (total_w + total_l) * 100) if (total_w + total_l) > 0 else 0

print(f"\n{'='*60}")
print(f"  COMBINED SEASON (HIGH + MODERATE)")
print(f"{'='*60}")
print(f"  TOTAL: {total_w}-{total_l} ({pct:.1f}%) | {total_u:+.1f} units")
