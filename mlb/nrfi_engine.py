import os
import statsapi
from datetime import datetime
from nrfi_data import get_pitcher_first_inning_stats, get_batter_xwoba_vs_hand
from nrfi_model import evaluate_game

def get_top_3_hitters(game_pk, team_type='away'):
    """
    Fetches the top 3 hitters from the lineup for the specified team.
    Returns a list of dicts: [{'id': 123, 'name': 'Player'}, ...]
    """
    try:
        box = statsapi.boxscore_data(game_pk)
        team_box = box.get(f'{team_type}Batters', [])
        
        # In statsapi boxscore_data, the batters list is usually ordered by batting order
        # But let's verify by looking at the battingOrder field if available, 
        # or just take the first 3 starting batters (those without pinch hit indicators like 'a', 'b', '1-')
        # statsapi.boxscore_data returns a list of player IDs (or dicts)
        # Wait, statsapi.boxscore_data(gamePk) returns dict like:
        # box['awayBatters'] = [id1, id2, ...]
        # Let's just grab the first 3 IDs that represent the starting top 3
        # We will use statsapi.get('game_boxscore') for safer lineup parsing
        
        raw_box = statsapi.get('game_boxscore', {'gamePk': game_pk})
        team_data = raw_box.get('teams', {}).get(team_type, {})
        batting_order_ids = team_data.get('battingOrder', [])
        
        top_3 = []
        for pid in batting_order_ids[:3]:
            player = team_data.get('players', {}).get(f'ID{pid}', {})
            name = player.get('person', {}).get('fullName', f'Unknown {pid}')
            top_3.append({'id': pid, 'name': name})
            
        return top_3
        
    except Exception as e:
        print(f"Error fetching hitters for game {game_pk}: {e}")
        return []

def run_nrfi_engine(target_date=None):
    if not target_date:
        target_date = datetime.now().strftime('%Y-%m-%d')
        
    print(f"Running NRFI Engine for {target_date}...")
    schedule = statsapi.schedule(date=target_date, sportId=1)
    
    if not schedule:
        print("No games found for this date.")
        return
        
    report_lines = []
    report_lines.append(f"# NRFI / YRFI Engine Report ({target_date})\n")
    report_lines.append("> [!TIP]\n> **YRFI Threat Score** represents the combined danger of the pitcher's 1st-inning struggles and the hitters' success vs that handedness. A score > 0.340 favors a run, < 0.290 favors a scoreless inning.\n")
    
    for game in schedule:
        game_pk = game['game_id']
        away_team = game['away_name']
        home_team = game['home_name']
        
        away_sp_name = game.get('away_probable_pitcher', '')
        home_sp_name = game.get('home_probable_pitcher', '')
        
        if not away_sp_name or not home_sp_name:
            continue
            
        print(f"\nProcessing: {away_team} @ {home_team}")
        
        # We need pitcher IDs to get their handedness and stats
        # statsapi schedule doesn't always give pitcher ID directly, let's get it from the game feed or just use player lookup
        try:
            # Safest way to get handedness and ID is from probable pitchers in the game feed
            game_feed = statsapi.get('game', {'gamePk': game_pk})
            probables = game_feed.get('gameData', {}).get('probablePitchers', {})
            
            away_sp_id = probables.get('away', {}).get('id')
            home_sp_id = probables.get('home', {}).get('id')
            
            if not away_sp_id or not home_sp_id:
                print(f"Skipping {away_team} @ {home_team}: Missing SP IDs.")
                continue
                
            # Get pitcher handedness (needed for batter splits)
            away_sp_throws = statsapi.get('people', {'personIds': away_sp_id}).get('people', [])[0].get('pitchHand', {}).get('code', 'R')
            home_sp_throws = statsapi.get('people', {'personIds': home_sp_id}).get('people', [])[0].get('pitchHand', {}).get('code', 'R')
            
        except Exception as e:
            print(f"Error fetching SP details: {e}")
            continue

        print(f"Fetching Pitcher Stats...")
        away_sp_stats = get_pitcher_first_inning_stats(away_sp_id)
        home_sp_stats = get_pitcher_first_inning_stats(home_sp_id)
        
        print(f"Fetching Hitters...")
        away_top_3 = get_top_3_hitters(game_pk, 'away')
        home_top_3 = get_top_3_hitters(game_pk, 'home')
        
        if not away_top_3 or not home_top_3:
            print(f"Skipping {away_team} @ {home_team}: Lineups not available yet.")
            continue
            
        away_hitters_stats = []
        for h in away_top_3:
            h_stat = get_batter_xwoba_vs_hand(h['id'], home_sp_throws)
            if h_stat:
                h_stat['name'] = h['name']
                away_hitters_stats.append(h_stat)
                
        home_hitters_stats = []
        for h in home_top_3:
            h_stat = get_batter_xwoba_vs_hand(h['id'], away_sp_throws)
            if h_stat:
                h_stat['name'] = h['name']
                home_hitters_stats.append(h_stat)
                
        print("Evaluating Matchup...")
        evaluation = evaluate_game(away_hitters_stats, home_sp_stats, home_hitters_stats, away_sp_stats)
        
        # Format markdown output
        report_lines.append(f"## {away_team} @ {home_team}")
        report_lines.append(f"**Recommendation:** **{evaluation['recommendation']}**\n")
        
        report_lines.append("### Top 1st (Away Hitters vs Home SP)")
        p_xwoba = home_sp_stats['xwoba_1st'] if home_sp_stats else "N/A"
        report_lines.append(f"- **{home_sp_name} (Throws: {home_sp_throws})**: 1st Inning xwOBA Allowed: {p_xwoba}")
        
        for h in away_hitters_stats:
            report_lines.append(f"  - {h['name']}: xwOBA vs {home_sp_throws}HP: {h['xwoba_vs_hand']}")
        report_lines.append(f"- **Top 1st Threat Score:** {evaluation['top_inning_threat']}\n")
        
        report_lines.append("### Bottom 1st (Home Hitters vs Away SP)")
        p_xwoba2 = away_sp_stats['xwoba_1st'] if away_sp_stats else "N/A"
        report_lines.append(f"- **{away_sp_name} (Throws: {away_sp_throws})**: 1st Inning xwOBA Allowed: {p_xwoba2}")
        
        for h in home_hitters_stats:
            report_lines.append(f"  - {h['name']}: xwOBA vs {away_sp_throws}HP: {h['xwoba_vs_hand']}")
        report_lines.append(f"- **Bottom 1st Threat Score:** {evaluation['bottom_inning_threat']}\n")
        report_lines.append("---\n")

    out_file = f"nrfi_report_{target_date}.md"
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
        
    print(f"Report saved to {out_file}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the NRFI Engine")
    parser.add_argument('--date', type=str, help="Date to run the engine for (YYYY-MM-DD). Defaults to today.", default=None)
    args = parser.parse_args()
    
    run_nrfi_engine(args.date)
