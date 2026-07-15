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

from fetch_schedule import get_today_games
from data_fetcher import get_team_metrics, get_park_factor

from grade_f5 import grade_matchup_v6
from monte_carlo_f5 import run_monte_carlo_f5
from full_game_model import run_full_game_mc

def process_single_game(args):
    game, date_str = args
    
    away = game['away_team']
    home = game['home_team']
    ap = game.get('away_starter', 'TBD')
    hp = game.get('home_starter', 'TBD')
    
    # We use home stadium as venue name for park factor
    venue = game.get('home_team', 'KBO Stadium')
    effective_pf = get_park_factor(venue)
    
    print(f"Processing KBO: {away} @ {home} (PF: {effective_pf})")
    
    # 1. Fetch Team Stats (Proxy for pitcher stats since KBO probable pitchers are unavailable)
    away_team_stats = get_team_metrics(away)
    home_team_stats = get_team_metrics(home)
    
    # We use team average FIP for starting pitcher and bullpen
    ap_fip = away_team_stats['FIP']
    hp_fip = home_team_stats['FIP']
    
    away_wrc = away_team_stats['wRC+']
    home_wrc = home_team_stats['wRC+']
    
    # Default 5 innings for KBO starters
    ap_projected_ip = 5.0
    hp_projected_ip = 5.0
    
    live_weather_multiplier = 1.0 # Weather is disabled for KBO currently
    
    # 2. Run Top-Down Matchup Grader
    top_down = grade_matchup_v6(
        away, ap_fip, ap_fip, ap_projected_ip, away_wrc, away_wrc,
        home, hp_fip, hp_fip, hp_projected_ip, home_wrc, home_wrc,
        park_factor=effective_pf,
        weather_multiplier=live_weather_multiplier,
        away_pitcher_hand="R", # Generic
        home_pitcher_hand="R", # Generic
        away_form_factor=1.0,
        home_form_factor=1.0
    )
    
    # 3. Prepare Lineups for Monte Carlo (Generate generic lineups)
    away_lineup_ids = []
    home_lineup_ids = []
    
    # 4. Run Full Game Monte Carlo
    try:
        mc = run_full_game_mc(
            away_lineup_ids,
            home_lineup_ids,
            ap,
            hp,
            ap_fip,
            hp_fip,
            away_team_name=away,
            home_team_name=home,
            away_projected_ip=ap_projected_ip,
            home_projected_ip=hp_projected_ip,
            iterations=1000,
            park_factor=effective_pf,
            weather_context=None,
            sport_id=15, # KBO sport id
            away_pitcher_hand="R",
            home_pitcher_hand="R",
            umpire_profile=None,
            away_wrc=away_wrc,
            home_wrc=home_wrc,
            venue_name=venue,
            pure_core=True,
            away_bp_fip=ap_fip,
            home_bp_fip=hp_fip
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  [MC Full Game Error] {e}")
        mc = {'f5_total': 0, 'full_game_total': 0, 'away_full_runs': 0, 'home_full_runs': 0}

    # Format output for JSON
    game_json = {
        "away_team": away,
        "home_team": home,
        "pitchers": {
            "away": {
                "name": ap, "hand": "R", "fip": ap_fip,
                "fb_pct": 0.5, "gb_pct": 0.5, "k_rate": 0.2
            },
            "home": {
                "name": hp, "hand": "R", "fip": hp_fip,
                "fb_pct": 0.5, "gb_pct": 0.5, "k_rate": 0.2
            }
        },
        "environment": {
            "venue": venue,
            "park_factor": effective_pf,
            "weather": {
                "temp": 72, "wind_mph": 0, "wind_dir": "Calm", "is_indoor": False, "weather_multiplier": live_weather_multiplier,
                "weather_label": f"Weather multiplier: {live_weather_multiplier}"
            },
            "effective_pf": effective_pf,
            "env_display": {
                "signal": "NEUTRAL", "delta": 0, "park_flag": "NEUTRAL", "park_signal": "NEUTRAL",
                "weather_flag": "NEUTRAL", "weather_signal": "NEUTRAL", "umpire_flag": "NEUTRAL", "umpire_signal": "NEUTRAL",
                "lean": "NEUTRAL", "effective_pf": effective_pf, "effective_pf_note": "", "summary": ""
            }
        },
        "lineups_status": "Generic",
        "predictions": {
            "top_down_f5": top_down['projected_f5_total'],
            "mc_f5": mc.get('mc_total_runs'),
            "mc_f5_away": mc.get('away_mc_runs'),
            "mc_f5_home": mc.get('home_mc_runs'),
            "mc_late": mc.get('late_total'),
            "mc_full_game": mc.get('full_game_total'),
            "td_clamp_applied": False,
            "away_f5_form": {"factor": 1.0},
            "home_f5_form": {"factor": 1.0},
            "form_factor": "Not implemented"
        },
        "probabilities": {
            "under_3_5": mc.get('under_3_5_prob'),
            "under_4_5": mc.get('under_4_5_prob'),
            "under_5_5": mc.get('under_5_5_prob'),
            "full_over_7_5": mc.get('full_over_7_5_prob'),
            "full_over_8_5": mc.get('full_over_8_5_prob'),
            "full_over_9_5": mc.get('full_over_9_5_prob')
        },
        "action_matrix": {
            "adv_3_5": "Skip",
            "adv_4_5": "Skip",
            "adv_5_5": "Skip"
        },
        "version": "v4"
    }
    
    # Format output for Markdown Block
    md_block = f"""### {away} @ {home}
**Venue:** {venue} | **Time:** {game.get('game_time', 'TBD')}
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
    elif '/' in date_str:
        date_str = datetime.datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
        
    games = get_today_games(date_str)
    if not games:
        print("No KBO games found for today.")
        return
        
    print(f"Generating KBO Consensus Report for {len(games)} games...")
    
    results = [process_single_game((g, date_str)) for g in games]
    
    report_lines = []
    report_lines.append(f"# ⚾ KBO V4 Tuned Prediction Report (Sport ID: 15)")
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
    md_filename = f"consensus_f5_kbo_report_{date_str}.md"
    md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mlb', md_filename)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    # Write JSON Payload
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'baseball')
    os.makedirs(data_dir, exist_ok=True)
    json_filename = f"universal_predictions_KBO_{date_str}.json"
    json_path = os.path.join(data_dir, json_filename)
    
    frontend_payload = {
        "date": date_str,
        "league": "KBO",
        "mode": "generic",
        "total_predictions": len(json_data),
        "predictions": json_data
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(frontend_payload, f, indent=4)
        
    print(f"\nDone! Report written to {md_path}")
    print(f"JSON data bridged to {json_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KBO Consensus F5 Engine")
    parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format (defaults to today)")
    args = parser.parse_args()
    
    generate_consensus_report(date_str=args.date)
