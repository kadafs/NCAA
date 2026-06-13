import statsapi
import time

def get_league_fip(season=2026):
    start = time.time()
    try:
        # Get all 30 MLB teams
        teams = statsapi.get('teams', {'sportId': 1, 'season': season})['teams']
        
        total_hr = 0
        total_bb = 0
        total_hbp = 0
        total_k = 0
        total_ip = 0.0
        
        for t in teams:
            team_id = t['id']
            # Fetch pitching stats for the season
            try:
                data = statsapi.get('team_stats', {'teamId': team_id, 'group': 'pitching', 'stats': 'season', 'season': season})
                for stat_group in data.get('stats', []):
                    splits = stat_group.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        
                        hr = int(stats.get('homeRuns', 0))
                        bb = int(stats.get('baseOnBalls', 0))
                        hbp = int(stats.get('hitBatsmen', 0))
                        k = int(stats.get('strikeOuts', 0))
                        
                        ip_str = stats.get('inningsPitched', '0')
                        parts = str(ip_str).split('.')
                        full = float(parts[0])
                        thirds = float(parts[1]) / 3.0 if len(parts) > 1 else 0.0
                        ip = full + thirds
                        
                        total_hr += hr
                        total_bb += bb
                        total_hbp += hbp
                        total_k += k
                        total_ip += ip
                        break
            except Exception as e:
                print(f"Error fetching team {team_id}: {e}")
                
        if total_ip > 0:
            league_fip = ((13 * total_hr) + (3 * (total_bb + total_hbp)) - (2 * total_k)) / total_ip + 3.20
            print(f"League FIP for {season}: {league_fip:.3f}")
            print(f"Time taken: {time.time() - start:.2f} seconds")
            return league_fip
            
    except Exception as e:
        print(f"Global error: {e}")
        
get_league_fip(2026)
