import re

def analyze(filename):
    try:
        with open(filename, 'r', encoding='utf-16') as f:
            text = f.read()
    except UnicodeError:
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()

    days = text.split('Backtesting Date: ')[1:]
    print(f'Days found: {len(days)}')
    print(f"{'Date':<15} | {'W':<4} | {'L':<4} | {'Win%':<6} | Net")
    print('-' * 44)
    
    total_w = total_l = 0
    total_units = 0.0
    
    for d in days:
        date_str = d.split('\n')[0].strip()
        games = d.split('Processing: ')[1:]
        wins = losses = 0
        for g in games:
            if '(HIGH)' in g:
                if 'Grade: WIN' in g:
                    wins += 1
                elif 'Grade: LOSS' in g:
                    losses += 1
        total_w += wins
        total_l += losses
        day_units = wins - losses
        total_units += day_units
        total = wins + losses
        pct = (wins / total * 100) if total > 0 else 0
        print(f"{date_str:<15} | {wins:<4} | {losses:<4} | {pct:>5.1f}% | {day_units:>+5.1f}u")
    
    print('=' * 44)
    overall_pct = (total_w / (total_w + total_l) * 100) if (total_w + total_l) > 0 else 0
    print(f"HIGH CONF TOTAL: {total_w}-{total_l} ({overall_pct:.1f}%) | {total_units:+.1f} units")

analyze('backtest_results_may_june.log')
