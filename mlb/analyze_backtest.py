import re

with open('final_backtest_results.log', 'r') as f:
    text = f.read()

games = text.split('Processing: ')
print(f"Total games parsed: {len(games)}")

td_wins = td_losses = mc_wins = mc_losses = over_wins = over_losses = under_wins = under_losses = 0

for g in games[1:]:
    try:
        td = float(re.search(r'TD: ([\-\d\.]+)', g).group(1))
        mc = float(re.search(r'MC Under 4\.5 Prob: ([\d\.]+)', g).group(1))
        sig = re.search(r'-> Signal: ([A-Z]+)', g).group(1)
        runs_match = re.search(r'Actual F5 Runs: ([\d]+|None)', g).group(1)
        
        if runs_match == 'None': continue
        actual = int(runs_match)
        
        if sig == 'OVER':
            if actual > 4.5: over_wins += 1
            else: over_losses += 1
        elif sig == 'UNDER':
            if actual < 4.5: under_wins += 1
            else: under_losses += 1
            
        td_signal = 'UNDER' if td < 4.5 else 'OVER'
        if td_signal == 'UNDER':
            if actual < 4.5: td_wins += 1
            else: td_losses += 1
        else:
            if actual > 4.5: td_wins += 1
            else: td_losses += 1
            
        mc_signal = 'UNDER' if mc > 0.50 else 'OVER'
        if mc_signal == 'UNDER':
            if actual < 4.5: mc_wins += 1
            else: mc_losses += 1
        else:
            if actual > 4.5: mc_wins += 1
            else: mc_losses += 1

    except Exception as e:
        print(f"Error parsing game: {e}")

print(f'Combined OVER Bets: {over_wins}-{over_losses} ({(over_wins/(over_wins+over_losses)*100) if over_wins+over_losses>0 else 0:.1f}%)')
print(f'Combined UNDER Bets: {under_wins}-{under_losses} ({(under_wins/(under_wins+under_losses)*100) if under_wins+under_losses>0 else 0:.1f}%)')
print('-'*30)
print(f'TD Only (All Games): {td_wins}-{td_losses} ({(td_wins/(td_wins+td_losses)*100) if td_wins+td_losses>0 else 0:.1f}%)')
print(f'MC Only (All Games): {mc_wins}-{mc_losses} ({(mc_wins/(mc_wins+mc_losses)*100) if mc_wins+mc_losses>0 else 0:.1f}%)')
