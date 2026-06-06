import os
import datetime
from run_daily_f5 import get_today_games, get_pitcher_fip, get_team_wrc_proxy
from grade_f5 import grade_matchup
from fetch_lineups import get_lineup_for_game
from monte_carlo_f5 import run_monte_carlo_f5

def generate_consensus_report():
    games = get_today_games()
    if not games:
        print("No games found.")
        return
        
    print(f"Generating Consensus Report for {len(games)} games...")
    
    report_lines = []
    report_lines.append(f"# MLB F5 Consensus Picks - {datetime.datetime.now().strftime('%Y-%m-%d')}")
    report_lines.append("This report combines the Top-Down wRC+/FIP Model with a 10,000-iteration Monte Carlo Simulation.")
    report_lines.append("")
    
    for game in games:
        away = game['away_team']
        home = game['home_team']
        ap = game['away_pitcher']
        hp = game['home_pitcher']
        gid = game['game_id']
        
        print(f"Processing: {away} @ {home}")
        
        # 1. Top-Down Model
        ap_fip = get_pitcher_fip(ap)
        hp_fip = get_pitcher_fip(hp)
        away_wrc = get_team_wrc_proxy(away)
        home_wrc = get_team_wrc_proxy(home)
        
        top_down = grade_matchup(away, ap_fip, away_wrc, home, hp_fip, home_wrc)
        td_total = top_down['projected_f5_total']
        
        # 2. Monte Carlo Model
        lineups = get_lineup_for_game(gid)
        # Check if lineups exist, otherwise MC uses league average generic lineups.
        lineups_status = "Confirmed" if lineups['away'] else "Projected (Generic)"
        mc = run_monte_carlo_f5(lineups['away'], lineups['home'], ap, hp, ap_fip, hp_fip, iterations=10000)
        
        # 3. Betting Matrix Logic
        def get_advice(line, under_prob):
            td_signal = "UNDER" if td_total < line else "OVER"
            mc_signal = "NEUTRAL"
            if under_prob >= 0.52:
                mc_signal = "UNDER"
            elif under_prob <= 0.48:
                mc_signal = "OVER"
                
            if td_signal == mc_signal:
                confidence = "HIGH" if (under_prob >= 0.58 or under_prob <= 0.42) else "MODERATE"
                return f"Bet **{mc_signal}**"
            return "Skip"

        adv_3_5 = get_advice(3.5, mc['under_3_5_prob'])
        adv_4_5 = get_advice(4.5, mc['under_4_5_prob'])
        adv_5_5 = get_advice(5.5, mc['under_5_5_prob'])
        
        # 4. Format Output
        report_lines.append(f"### {away} ({ap}) @ {home} ({hp})")
        report_lines.append(f"- **Top-Down Projected F5 Total:** {td_total} Runs")
        report_lines.append(f"- **Monte Carlo Simulated F5 Total:** {mc['mc_total_runs']} Runs (Lineups: {lineups_status})")
        report_lines.append(f"- 🎯 **ACTION MATRIX (Based on your Sportsbook's Line):**")
        report_lines.append(f"  - If Line is **3.5** -> {adv_3_5} | MC Under Probability: {int(mc['under_3_5_prob']*100)}%")
        report_lines.append(f"  - If Line is **4.5** -> {adv_4_5} | MC Under Probability: {int(mc['under_4_5_prob']*100)}%")
        report_lines.append(f"  - If Line is **5.5** -> {adv_5_5} | MC Under Probability: {int(mc['under_5_5_prob']*100)}%")
        report_lines.append("")
        
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consensus_f5_report.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    print(f"\nDone! Report written to {output_path}")

if __name__ == "__main__":
    generate_consensus_report()
