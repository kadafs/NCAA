import pandas as pd
import numpy as np

def generate_v6_premium_45_gatekeeper(df):
    """
    V6 Premium Gatekeeper Engine: Restricts active betting executions exclusively 
    to the 4.5 market line when available odds are at least 1.80.
    Generalized mathematically to eliminate hardcoded team name constraints.
    """
    # Foundational metrics
    df['Index'] = (df['TD'] - df['MC']).abs()
    df['Combined_Average'] = (df['TD'] + df['MC']) / 2.0
    
    # Restrict script to your specific market parameters
    TARGET_LINE = 4.5
    MIN_ODDS = 1.80
    
    # Dynamic Veto Degradation based on season progression (Sample Size Check)
    avg_games = df['Games'].mean() if 'Games' in df.columns else 40.0
    if avg_games > 65:
        veto_threshold = 0.10
    elif avg_games > 45:
        veto_threshold = 0.125
    else:
        veto_threshold = 0.150

    betting_slate = []
    error_logs = []
    flagged_games = set()
    structured_data = {}

    # -------------------------------------------------------------------------
    # LAYER 1: AUTOMATED ERROR LOGGING & QUARANTINE
    # -------------------------------------------------------------------------
    for idx, row in df.iterrows():
        game = row['Game']
        if abs(row['MCaw'] - row['MChm']) > 0.90 and abs(row['AwSP'] - row['HmSP']) < 0.60:
            flagged_games.add(game)
            error_logs.append(
                f"### 3. Automated Error Log: Asymmetric Check Flagged\n\n"
                f"Quarantined: **{game}** (TD: {row['TD']:.2f} | MC: {row['MC']:.2f})\n"
                f"*   *The Flag:* Distribution asymmetry detected. Review SP profiles.\n"
            )
            structured_data[game] = {
                "category": "Quarantined",
                "action": "SKIP",
                "reason": "Distribution asymmetry detected. Review SP profiles."
            }

    # -------------------------------------------------------------------------
    # LAYER 2: ELITE PREMIUM 4.5 FILTERING LOOP
    # -------------------------------------------------------------------------
    strategy_counter = 1
    for idx, row in df.iterrows():
        game = row['Game']
        if game in flagged_games:
            continue
            
        # Market validation checklist checks
        market_line = row.get('Market_Line', 4.5)
        market_odds = row.get('Market_Odds', 1.85)
        
        if market_line != TARGET_LINE or market_odds < MIN_ODDS:
            structured_data[game] = {
                "category": "Market Exclusion",
                "action": "SKIP",
                "reason": f"Line is {market_line} or odds ({market_odds}) under 1.80 threshold."
            }
            continue

        # LINE-CROSSING VETO CHECK (Absolute Model Disagreement Shield)
        if (row['TD'] > TARGET_LINE and row['MC'] < TARGET_LINE) or (row['TD'] < TARGET_LINE and row['MC'] > TARGET_LINE):
            structured_data[game] = {
                "category": "Line-Crossing Veto",
                "action": "SKIP",
                "reason": "Models conflict across the 4.5 line."
            }
            continue

        # Determine direction based on your combined averages
        side = "UNDER" if row['Combined_Average'] < TARGET_LINE else "OVER"
        edge = abs(row['Combined_Average'] - TARGET_LINE)

        # A. HIGH DIVERGENCE STRATEGY MATRIX (Index > 0.50)
        if row['Index'] > 0.50:
            # Case 1: Team Bias Veto (Park Noise Pollution)
            if abs(row['Realized_PF'] - row['Static_PF']) > veto_threshold:
                mc_side = "UNDER" if row['MC'] < TARGET_LINE else "OVER"
                reason = f"Team Bias Veto Active. Trusting MC; TD blinded by unregressed park variance ({abs(row['Realized_PF'] - row['Static_PF'])*100:.1f}%)."
                betting_slate.append(f"{strategy_counter}. **{game}** ──► **BET F5 {mc_side}** (Odds: {market_odds:.2f})\n    *   *System Note:* {reason}\n")
                structured_data[game] = {"category": "High-Value Strategy", "action": f"BET F5 {mc_side}", "reason": reason, "odds": market_odds}
                strategy_counter += 1
                
            # Case 2: Explosive Fly-Ball Tail Risk
            elif row['Blended_PF'] > 1.10 and (row['Aw_HR_FB'] > 0.14 or row['Hm_HR_FB'] > 0.14):
                reason = f"Explosive Tail Risk: MC capturing non-linear fly-ball profiles in hitter-friendly park ({row['Blended_PF']:.3f}x)."
                betting_slate.append(f"{strategy_counter}. **{game}** ──► **BET F5 {side}** (Odds: {market_odds:.2f})\n    *   *System Note:* {reason}\n")
                structured_data[game] = {"category": "High-Value Strategy", "action": f"BET F5 {side}", "reason": reason, "odds": market_odds}
                strategy_counter += 1
                
            # Case 3: Strikeout/Walk Volatility Noise
            elif (row['Aw_K_Rate'] + row['Hm_K_Rate'] > 0.48) or (row['Aw_BB_Rate'] + row['Hm_BB_Rate'] > 0.20):
                td_side = "UNDER" if row['TD'] < TARGET_LINE else "OVER"
                reason = "Volatility Veto: High true-outcome pitcher metrics. MC sequence noise flagged; trusting TD."
                betting_slate.append(f"{strategy_counter}. **{game}** ──► **BET F5 {td_side}** (Odds: {market_odds:.2f})\n    *   *System Note:* {reason}\n")
                structured_data[game] = {"category": "High-Value Strategy", "action": f"BET F5 {td_side}", "reason": reason, "odds": market_odds}
                strategy_counter += 1
                
            # Case 4: Pure Distance Edge
            elif edge >= 0.20:
                better_model = "MC" if abs(row['MC'] - TARGET_LINE) > abs(row['TD'] - TARGET_LINE) else "TD"
                dist_side = "UNDER" if row[better_model.upper()] < TARGET_LINE else "OVER"
                reason = f"Divergent baseline alignment confirms line value. Trusting {better_model} via pure distance edge."
                betting_slate.append(f"{strategy_counter}. **{game}** ──► **BET F5 {dist_side}** (Odds: {market_odds:.2f})\n    *   *System Note:* {reason}\n")
                structured_data[game] = {"category": "High-Value Strategy", "action": f"BET F5 {dist_side}", "reason": reason, "odds": market_odds}
                strategy_counter += 1

        # B. HIGH-CONFIDENCE SYSTEMATIC ALIGNMENT (Index < 0.25)
        elif row['Index'] < 0.25 and edge >= 0.10:
            reason = "Engine Convergence: Models perfectly aligned with measurable market edge."
            betting_slate.append(f"*   **{game}** ──► **BET F5 {side}** (Odds: {market_odds:.2f})\n    *   *System Note:* {reason}\n")
            structured_data[game] = {"category": "High-Confidence", "action": f"BET F5 {side}", "reason": reason, "odds": market_odds}

    # -------------------------------------------------------------------------
    # LAYER 3: REPORT COMPILATION
    # -------------------------------------------------------------------------
    report = ["# Automated V6 Premium 4.5 Gatekeeper Report\n", "## Active Portfolio Recommendations"]
    if betting_slate:
        report.extend(betting_slate)
    else:
        report.append("No games matched the precise 4.5 line and 1.80+ odds execution requirements for tonight.\n")
        
    if error_logs: 
        report.extend(["\n"] + error_logs)
    
    return "\n".join(report), structured_data
