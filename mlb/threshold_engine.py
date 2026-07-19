import pandas as pd

def generate_league_specific_threshold_report(df, sport_id):
    """
    League-Specific Threshold Engine:
    Replaces the legacy Gatekeeper. Evaluates games based on statically proven 
    league thresholds for Maximum ROI on F5 Over bets.
    
    - MLB (1): MC >= 5.50
    - AAA (11): MC >= 5.40 
    - AA (12): MC >= 4.60 AND TD >= 4.60
    - LMB (23): MC 4.60-5.10 AND TD 4.60-5.10
    """
    betting_slate = []
    structured_data = {}
    
    try:
        sport_id = int(sport_id)
    except (ValueError, TypeError):
        sport_id = 1 # Default to MLB if invalid
    
    strategy_counter = 1
    for idx, row in df.iterrows():
        game = row.get('Game', 'Unknown Game')
        mc = float(row.get('MC', 0))
        td = float(row.get('TD', 0))
        
        action = None
        reason = None
        category = None
        
        market_line = row.get('Market_Line', 4.5)
        market_odds = row.get('Market_Odds', 1.85)
        
        # We only execute on the 4.5 line for these F5 Over systems
        if market_line != 4.5 or market_odds < 1.80:
            continue
            
        if sport_id == 1: # MLB
            if mc >= 5.50 and td >= 5.50:
                action = "BET F5 OVER 4.5"
                reason = f"MLB Double Convergence Met (MC={mc:.2f} >= 5.50 & TD={td:.2f} >= 5.50)"
                category = "Threshold Play"
                
        elif sport_id == 11: # AAA
            if mc >= 5.40 and td >= 5.40:
                action = "BET F5 OVER 4.5"
                reason = f"AAA Double Convergence Met (MC={mc:.2f} >= 5.40 & TD={td:.2f} >= 5.40)"
                category = "Threshold Play"
                
        elif sport_id == 12: # AA
            if mc >= 4.60 and td >= 4.60:
                action = "BET F5 OVER 4.5"
                reason = f"AA Double Convergence Met (MC={mc:.2f} >= 4.60 & TD={td:.2f} >= 4.60)"
                category = "Threshold Play"
                
        elif sport_id == 23: # LMB
            if (4.60 <= mc <= 5.10) and (4.60 <= td <= 5.10):
                action = "BET F5 OVER 4.5"
                reason = f"LMB Mid-Range Double Convergence Met (MC={mc:.2f} & TD={td:.2f} in 4.60-5.10 range)"
                category = "Threshold Play"
        else:
            # Fallback threshold if new league is ever added
            if mc >= 5.50 and td >= 5.50:
                action = "BET F5 OVER 4.5"
                reason = f"Generic Double Convergence Met (MC={mc:.2f} >= 5.50 & TD={td:.2f} >= 5.50)"
                category = "Threshold Play"
        
        if action:
            betting_slate.append(f"{strategy_counter}. **{game}** ──► **{action}**\n    *   *System Note:* {reason}\n")
            structured_data[game] = {"category": category, "action": action, "reason": reason}
            strategy_counter += 1
            
    report = ["# Automated League-Specific Threshold Report\n", "## Active Portfolio Recommendations"]
    if betting_slate:
        report.extend(betting_slate)
    else:
        report.append("No games met the strict league-specific thresholds for today.\n")
        
    return "\n".join(report), structured_data
