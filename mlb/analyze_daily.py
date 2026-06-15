import re

def analyze_daily_high_confidence():
    try:
        with open('final_backtest_results.log', 'r', encoding='utf-16') as f:
            text = f.read()
    except UnicodeError:
        with open('final_backtest_results.log', 'r', encoding='utf-8') as f:
            text = f.read()

    days = text.split('Backtesting Date: ')[1:]
    
    print(f"{'Date':<15} | {'Wins':<5} | {'Losses':<6} | {'Win %':<6} | {'Net Units':<8}")
    print("-" * 50)
    
    total_w = 0
    total_l = 0
    total_units = 0.0

    for d in days:
        date_str = d.split('\n')[0].strip()
        games = d.split('Processing: ')[1:]
        
        wins = 0
        losses = 0
        
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
        win_pct = (wins / total * 100) if total > 0 else 0
        
        print(f"{date_str:<15} | {wins:<5} | {losses:<6} | {win_pct:>5.1f}% | {day_units:>+7.1f}u")
        
    print("=" * 50)
    overall_pct = (total_w / (total_w + total_l) * 100) if (total_w + total_l) > 0 else 0
    print(f"HIGH CONFIDENCE RECORD : {total_w} - {total_l} ({overall_pct:.1f}%) | {total_units:+.1f} units")

if __name__ == '__main__':
    analyze_daily_high_confidence()
