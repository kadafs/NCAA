import pandas as pd
import numpy as np

def generate_v5_mathematical_gatekeeper(df):
    """
    V5 Gatekeeper Engine: Completely generalized logic using mathematical 
    thresholds instead of hardcoded team strings.
    """
    df['Index'] = (df['TD'] - df['MC']).abs()
    df['Combined_Average'] = (df['TD'] + df['MC']) / 2.0
    
    high_value_strategy = []
    high_confidence = []
    error_logs = []
    flagged_games = set()

    structured_data = {}

    # 1. ERROR LOG LAYER: PROGRAMMATIC ASYMMETRIC FILTER
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
                "reason": "Distribution asymmetry detected. Review SP profiles."
            }

    # 2. CONDITIONAL BETTING LAYER
    strategy_counter = 1
    for idx, row in df.iterrows():
        game = row['Game']
        if game in flagged_games:
            continue
            
        # -- HIGH DIVERGENCE MATHEMATICAL STRATEGY MATRIX --
        if row['Index'] > 0.50:
            game_report = f"{strategy_counter}. **{game}** (Index: {row['Index']:.2f})\n"
            matrix_lines = []
            structured_lines = {}
            
            for line in [3.5, 4.5, 5.5]:
                # LINE-CROSSING VETO: Pure mathematical check
                if (row['TD'] > line and row['MC'] < line) or (row['TD'] < line and row['MC'] > line):
                    matrix_lines.append(f"    *   **IF Line is {line}:** Hard Skip (Models conflict across line)")
                    structured_lines[str(line)] = {"action": "Skip", "reason": "Models conflict across line"}
                    continue
                
                # Dynamic Check 1: Park Factor Noise Pollution
                if abs(row['Realized_PF'] - row['Static_PF']) > 0.15:
                    side = 'Under' if row['MC'] < line else 'Over'
                    reason = f"Trust MC; TD blinded by extreme unregressed park variance ({abs(row['Realized_PF'] - row['Static_PF'])*100:.1f}%)."
                    matrix_lines.append(f"    *   **IF Line is {line}:** BET F5 {side.upper()} ──► {reason}")
                    structured_lines[str(line)] = {"action": f"BET F5 {side.upper()}", "reason": reason}
                
                # Dynamic Check 2: Explosive Fly-Ball Tail Risk
                elif row['Blended_PF'] > 1.10 and (row['Aw_HR_FB'] > 0.14 or row['Hm_HR_FB'] > 0.14):
                    side = 'Under' if row['MC'] < line else 'Over'
                    reason = f"Trust MC; MC capturing non-linear tail risk of fly-ball profiles in a hitter-friendly park ({row['Blended_PF']:.3f}x)."
                    matrix_lines.append(f"    *   **IF Line is {line}:** BET F5 {side.upper()} ──► {reason}")
                    structured_lines[str(line)] = {"action": f"BET F5 {side.upper()}", "reason": reason}
                
                # Dynamic Check 3: Strikeout/Walk Volatility Noise
                elif (row['Aw_K_Rate'] + row['Hm_K_Rate'] > 0.48) or (row['Aw_BB_Rate'] + row['Hm_BB_Rate'] > 0.20):
                    side = 'Under' if row['TD'] < line else 'Over'
                    reason = "Trust TD; High true-outcome pitcher metrics detected. MC vulnerable to sequence pacing noise."
                    matrix_lines.append(f"    *   **IF Line is {line}:** BET F5 {side.upper()} ──► {reason}")
                    structured_lines[str(line)] = {"action": f"BET F5 {side.upper()}", "reason": reason}
                
                # Default Generalized Backup
                else:
                    better_model = "MC" if abs(row['MC'] - line) > abs(row['TD'] - line) else "TD"
                    side = 'Under' if row[better_model] < line else 'Over'
                    reason = f"Trust {better_model} via pure distance edge."
                    matrix_lines.append(f"    *   **IF Line is {line}:** BET F5 {side.upper()} ──► {reason}")
                    structured_lines[str(line)] = {"action": f"BET F5 {side.upper()}", "reason": reason}

            if matrix_lines:
                game_report += "\n".join(matrix_lines) + "\n"
                high_value_strategy.append(game_report)
                structured_data[game] = {
                    "category": "High-Value Strategy",
                    "index": row['Index'],
                    "lines": structured_lines
                }
                strategy_counter += 1

        # -- HIGH-CONFIDENCE SYSTEMATIC ALIGNMENT --
        elif row['Index'] < 0.25:
            agree_report = f"*   **{game}** (Index: {row['Index']:.2f} | TD: {row['TD']:.2f} | MC: {row['MC']:.2f})\n"
            matrix_lines = []
            structured_lines = {}
            
            for line in [3.5, 4.5, 5.5]:
                if abs(row['Combined_Average'] - line) >= 0.10:
                    side = "UNDER" if row['Combined_Average'] < line else "OVER"
                    reason = "Clean value engine agreement"
                    matrix_lines.append(f"    *   IF Line is {line} ──► **BET F5 {side}** ({reason})")
                    structured_lines[str(line)] = {"action": f"BET F5 {side}", "reason": reason}
                else:
                    reason = "No actionable betting margin"
                    matrix_lines.append(f"    *   IF Line is {line} ──► SKIP ({reason})")
                    structured_lines[str(line)] = {"action": "Skip", "reason": reason}
            
            agree_report += "\n".join(matrix_lines) + "\n"
            high_confidence.append(agree_report)
            structured_data[game] = {
                "category": "High-Confidence",
                "index": row['Index'],
                "lines": structured_lines
            }

    # REPORT PRINT BLOCK
    report = ["# Automated V5 Mathematical F5 Gatekeeper Report\n", "## 1. Conditional High-Value Strategy Matrix"]
    report.extend(high_value_strategy if high_value_strategy else ["No strategy matrix targets."])
    report.append("\n## 2. High-Confidence Line Lookup (Index < 0.25)")
    report.extend(high_confidence if high_confidence else ["No high-confidence alignments."])
    if error_logs: report.extend(["\n"] + error_logs)
    
    return "\n".join(report), structured_data
