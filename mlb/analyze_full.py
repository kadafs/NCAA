import re

def analyze(filename, label):
    try:
        with open(filename, 'r', encoding='utf-16') as f:
            text = f.read()
    except UnicodeError:
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()

    games = text.split('Processing: ')[1:]

    all_w = all_l = 0
    high_w = high_l = 0
    mod_w = mod_l = 0
    over_w = over_l = 0
    under_w = under_l = 0
    over_high_w = over_high_l = 0
    under_high_w = under_high_l = 0

    for g in games:
        try:
            sig_match = re.search(r'-> Signal: ([A-Z]+) \(([A-Z]+)\)', g)
            runs_match = re.search(r'Actual F5 Runs: (\d+|None)', g)
            grade_match = re.search(r'Grade: ([A-Z]+)', g)

            if not (sig_match and runs_match and grade_match):
                continue
            if runs_match.group(1) == 'None':
                continue

            direction = sig_match.group(1)   # OVER or UNDER
            confidence = sig_match.group(2)  # HIGH or MODERATE
            actual = int(runs_match.group(1))
            grade = grade_match.group(1)

            if grade == 'PENDING':
                continue

            win = grade == 'WIN'

            # All bets (HIGH + MODERATE)
            if grade == 'WIN': all_w += 1
            elif grade == 'LOSS': all_l += 1

            # By confidence
            if confidence == 'HIGH':
                if win: high_w += 1
                else: high_l += 1
            elif confidence == 'MODERATE':
                if win: mod_w += 1
                else: mod_l += 1

            # By direction (all confidence)
            if direction == 'OVER':
                if win: over_w += 1
                else: over_l += 1
            elif direction == 'UNDER':
                if win: under_w += 1
                else: under_l += 1

            # By direction (HIGH only)
            if confidence == 'HIGH':
                if direction == 'OVER':
                    if win: over_high_w += 1
                    else: over_high_l += 1
                elif direction == 'UNDER':
                    if win: under_high_w += 1
                    else: under_high_l += 1

        except Exception:
            pass

    def pct(w, l):
        return f"{w/(w+l)*100:.1f}%" if (w+l) > 0 else "N/A"

    print(f"\n{'='*52}")
    print(f"  {label}")
    print(f"{'='*52}")
    print(f"  {'Category':<30} | {'W-L':<12} | Win%")
    print(f"  {'-'*50}")
    print(f"  {'All Bets (HIGH + MODERATE)':<30} | {all_w}-{all_l:<9} | {pct(all_w, all_l)}")
    print(f"  {'HIGH Confidence Only':<30} | {high_w}-{high_l:<9} | {pct(high_w, high_l)}")
    print(f"  {'MODERATE Confidence Only':<30} | {mod_w}-{mod_l:<9} | {pct(mod_w, mod_l)}")
    print(f"  {'-'*50}")
    print(f"  {'OVER Bets (All Confidence)':<30} | {over_w}-{over_l:<9} | {pct(over_w, over_l)}")
    print(f"  {'UNDER Bets (All Confidence)':<30} | {under_w}-{under_l:<9} | {pct(under_w, under_l)}")
    print(f"  {'-'*50}")
    print(f"  {'OVER Bets (HIGH Only)':<30} | {over_high_w}-{over_high_l:<9} | {pct(over_high_w, over_high_l)}")
    print(f"  {'UNDER Bets (HIGH Only)':<30} | {under_high_w}-{under_high_l:<9} | {pct(under_high_w, under_high_l)}")

    return {
        'all_w': all_w, 'all_l': all_l,
        'high_w': high_w, 'high_l': high_l,
        'mod_w': mod_w, 'mod_l': mod_l,
        'over_w': over_w, 'over_l': over_l,
        'under_w': under_w, 'under_l': under_l,
        'over_high_w': over_high_w, 'over_high_l': over_high_l,
        'under_high_w': under_high_w, 'under_high_l': under_high_l,
    }

r1 = analyze('final_backtest_results.log', 'PERIOD 1: Apr 10 - May 10 (final_backtest_results.log)')
r2 = analyze('backtest_results_may_june.log', 'PERIOD 2: May 11 - Jun 13 (backtest_results_may_june.log)')

def pct(w, l):
    return f"{w/(w+l)*100:.1f}%" if (w+l) > 0 else "N/A"

print(f"\n{'='*52}")
print(f"  COMBINED SEASON TOTALS")
print(f"{'='*52}")
print(f"  {'Category':<30} | {'W-L':<12} | Win%")
print(f"  {'-'*50}")
for key in ['all', 'high', 'mod', 'over', 'under', 'over_high', 'under_high']:
    w = r1[f'{key}_w'] + r2[f'{key}_w']
    l = r1[f'{key}_l'] + r2[f'{key}_l']
    labels = {
        'all': 'All Bets (HIGH + MODERATE)',
        'high': 'HIGH Confidence Only',
        'mod': 'MODERATE Confidence Only',
        'over': 'OVER Bets (All Confidence)',
        'under': 'UNDER Bets (All Confidence)',
        'over_high': 'OVER Bets (HIGH Only)',
        'under_high': 'UNDER Bets (HIGH Only)',
    }
    if key in ['over_high', 'under_high']:
        print(f"  {'-'*50}")
    print(f"  {labels[key]:<30} | {w}-{l:<9} | {pct(w,l)}")
