import sys
import os

# Ensure mlb directory is in python path
sys.path.append(os.path.abspath('mlb'))
from park_factors import get_park_factor_details

venues_june24 = {
    'Mets': 'Citi Field',
    'White Sox': 'Guaranteed Rate Field',
    'Rockies': 'Coors Field',
    'Angels': 'Angel Stadium',
    'Pirates': 'PNC Park',
    'Tigers': 'Comerica Park',
    'Nationals': 'Nationals Park',
    'Blue Jays': 'Rogers Centre',
    'Twins': 'Target Field',
    'Cardinals': 'Busch Stadium',
    'Padres': 'Petco Park',
}

bets = {
    'Mets': 'UNDER',
    'White Sox': 'OVER',
    'Rockies': 'OVER',
    'Angels': 'OVER',
    'Pirates': 'UNDER',
    'Tigers': 'UNDER',
    'Nationals': 'OVER',
    'Blue Jays': 'OVER',
    'Twins': 'UNDER',
    'Cardinals': 'OVER',
    'Padres': 'OVER',
}

print("Running fast filter check for June 24 traps...")
traps_avoided = 0
for team, venue in venues_june24.items():
    details = get_park_factor_details(venue)
    pf = details.get('static', 1.0)
    realized = details.get('realized', 1.0)
    diff = realized - pf
    bet = bets[team]
    
    team_bias_skip = False
    if bet == 'OVER' and diff > 0.15:
        team_bias_skip = True
    elif bet == 'UNDER' and diff < -0.15:
        team_bias_skip = True
        
    print(f"{venue} ({team}) -> Static: {pf:.3f}, Realized: {realized:.3f}, Diff: {diff:.3f}")
    if team_bias_skip:
        traps_avoided += 1
        print(f"  -> TRAP AVOIDED! Original Bet: {bet} would have been SKIPPED by Team Bias Veto.")
        
print(f"\nTotal Traps Avoided by Team Bias Veto on June 24: {traps_avoided}")
