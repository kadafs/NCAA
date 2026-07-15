import os
import sys
import json
import time
import datetime
from multiprocessing import Pool, cpu_count

# Add mlb to path to import the mathematical engines
mlb_path = os.path.join(os.path.dirname(__file__), '..', 'mlb')
sys.path.append(os.path.abspath(mlb_path))

sys.stdout.reconfigure(encoding='utf-8')

from data_fetcher import (
    get_today_games, get_pitcher_stats, get_team_stats, 
    get_team_bullpen_fip, get_team_f5_form_factor, get_weather_multiplier
)

from grade_f5 import grade_matchup_v6
from monte_carlo_f5 import run_monte_carlo_f5
from full_game_model import run_full_game_mc

def process_single_game(args):
    game, date_str = args
    
    away = game['away_team']
    home = game['home_team']
    ap = game['away_pitcher']
    hp = game['home_pitcher']
    venue = game.get('venue_name', 'Unknown')
    effective_pf = game.get('park_factor', 1.0)
    
    # We omit the venue from the print because it contains Japanese characters which crash the Windows console
    print(f"Processing NPB: {away} @ {home} (PF: {effective_pf})")
    
    # 1. Fetch Pitcher & Team Stats (Proxy Data Fetcher)
    ap_url = game.get('away_pitcher_url')
    hp_url = game.get('home_pitcher_url')
    ap_stats = get_pitcher_stats(ap, ap_url)
    hp_stats = get_pitcher_stats(hp, hp_url)
    
    away_team_stats = get_team_stats(away, opposing_pitcher_hand=hp_stats['hand'])
    home_team_stats = get_team_stats(home, opposing_pitcher_hand=ap_stats['hand'])
    
    away_bp = get_team_bullpen_fip(away)
    home_bp = get_team_bullpen_fip(home)
    
    away_form = get_team_f5_form_factor(away)
    home_form = get_team_f5_form_factor(home)
    
    away_factor = away_form.get('factor', 1.0)
    home_factor = home_form.get('factor', 1.0)
    
    live_weather_multiplier = get_weather_multiplier(venue)
    
    # 2. Run Top-Down Matchup Grader
    top_down = grade_matchup_v6(
        away, ap_stats['siera'], away_bp, ap_stats['projected_ip'], away_team_stats['vs_R'], away_team_stats['vs_L'],
        home, hp_stats['siera'], home_bp, hp_stats['projected_ip'], home_team_stats['vs_R'], home_team_stats['vs_L'],
        park_factor=effective_pf,
        weather_multiplier=live_weather_multiplier,
        away_pitcher_hand=ap_stats['hand'],
        home_pitcher_hand=hp_stats['hand'],
        away_form_factor=away_factor,
        home_form_factor=home_factor
    )
    
    # 3. Prepare Lineups for Monte Carlo (Generate generic lineups since we lack NPB live lineups)
    # The MC engine builds generic lineups internally if we pass empty lists and force_generic=True
    away_lineup_ids = []
    home_lineup_ids = []
    
    # 4. Run Full Game Monte Carlo (This yields both F5 and Full game totals)
    try:
        mc = run_full_game_mc(
            away_lineup_ids,
            home_lineup_ids,
            ap,
            hp,
            ap_stats['fip'],
            hp_stats['fip'],
            away_team_name=away,
            home_team_name=home,
            away_projected_ip=ap_stats['projected_ip'],
            home_projected_ip=hp_stats['projected_ip'],
            iterations=1000,
            park_factor=effective_pf,
            weather_context=None,
            sport_id=14,
            away_pitcher_hand=ap_stats['hand'],
            home_pitcher_hand=hp_stats['hand'],
            umpire_profile=None,
            away_wrc=away_team_stats['wrc_plus'],
            home_wrc=home_team_stats['wrc_plus'],
            venue_name=venue,
            pure_core=True,
            away_bp_fip=away_bp,
            home_bp_fip=home_bp
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  [MC Full Game Error] {e}")
        mc = {'f5_total': 0, 'full_game_total': 0, 'away_full_runs': 0, 'home_full_runs': 0}

    # Format output for JSON
    game_json = {
        "game_id": game['game_id'],
        "game_time": game['game_time'],
        "away_team": away,
        "home_team": home,
        "away_pitcher": ap,
        "home_pitcher": hp,
        "venue": venue,
        "park_factor": effective_pf,
        "weather_multiplier": 1.0, # Not implemented for NPB
        "top_down": top_down,
        "monte_carlo_f5": mc, # we pass mc for both, as it contains both subsets
        "monte_carlo_full": mc
    }
    
    # Format output for Markdown Block
    md_block = f"""### {away} @ {home}
**Venue:** {venue} | **Time:** {game['game_time']}
**Pitching:** {ap} vs {hp}

**Top-Down Engine (F5)**
* {away}: {top_down['away_expected_f5_runs']} expected runs
* {home}: {top_down['home_expected_f5_runs']} expected runs

**Monte Carlo Simulation**
* F5 Total: {mc.get('f5_total', 0):.2f}
* Full Game Total: {mc.get('full_game_total', 0):.2f}
"""
    return {
        'md_block': md_block,
        'json_data': game_json
    }

def generate_consensus_report(date_str=None):
    if not date_str:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
    games = get_today_games(date_str)
    if not games:
        print("No NPB games found for today.")
        return
        
    print(f"Generating NPB Consensus Report for {len(games)} games...")
    
    # Run serial to avoid multiprocessing headaches with dummy data for now
    results = [process_single_game((g, date_str)) for g in games]
    
    report_lines = []
    report_lines.append(f"# ⚾ NPB V4 Tuned Prediction Report (Sport ID: 14)")
    report_lines.append(f"**Date:** {date_str}")
    report_lines.append(f"**Generated:** {datetime.datetime.now().strftime('%H:%M:%S')}")
    report_lines.append(f"**Model Mode:** Generic Lineups (FORCED)")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    json_data = []
    for r in results:
        report_lines.append(r['md_block'])
        json_data.append(r['json_data'])
        
    # Write MD Report
    md_filename = f"consensus_f5_npb_report_{date_str}.md"
    md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mlb', md_filename)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    # Write JSON Payload
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'baseball')
    os.makedirs(data_dir, exist_ok=True)
    json_filename = f"universal_predictions_NPB_{date_str}.json"
    json_path = os.path.join(data_dir, json_filename)
    
    frontend_payload = {
        "date": date_str,
        "league": "NPB",
        "mode": "generic",
        "total_predictions": len(json_data),
        "predictions": json_data
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(frontend_payload, f, indent=4)
        
    print(f"\nDone! Report written to {md_path}")
    print(f"JSON data bridged to {json_path}")

if __name__ == "__main__":
    generate_consensus_report()
