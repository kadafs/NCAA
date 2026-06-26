import os
import json
import datetime
import statsapi
from park_factors import MLB_PARK_FACTORS

def main():
    start_dt = datetime.date(2026, 3, 28)
    end_dt = datetime.date.today()
    
    venue_stats = {}
    total_runs = 0
    total_games = 0
    
    current_start = start_dt
    while current_start <= end_dt:
        current_end = min(current_start + datetime.timedelta(days=7), end_dt)
        s_str = current_start.strftime("%Y-%m-%d")
        e_str = current_end.strftime("%Y-%m-%d")
        
        print(f"Fetching {s_str} to {e_str}...")
        games_data = statsapi.get('schedule', {'sportId': 1, 'startDate': s_str, 'endDate': e_str, 'hydrate': 'linescore'})
        for date_obj in games_data.get('dates', []):
            for g in date_obj.get('games', []):
                status = g.get('status', {}).get('abstractGameState')
                if status not in ['Final']:
                    continue
                    
                venue = g.get('venue', {}).get('name', 'Unknown')
                linescore = g.get('linescore', {})
                innings = linescore.get('innings', [])
                if len(innings) < 5:
                    continue
                    
                away_runs = sum(inn.get('away', {}).get('runs', 0) for inn in innings[:5] if 'runs' in inn.get('away', {}))
                home_runs = sum(inn.get('home', {}).get('runs', 0) for inn in innings[:5] if 'runs' in inn.get('home', {}))
                runs = away_runs + home_runs
                
                if venue not in venue_stats:
                    venue_stats[venue] = {'games': 0, 'runs': 0}
                venue_stats[venue]['games'] += 1
                venue_stats[venue]['runs'] += runs
                total_runs += runs
                total_games += 1
        
        current_start = current_end + datetime.timedelta(days=1)
        
    if total_games == 0:
        print("No games found.")
        return
        
    league_avg_runs = total_runs / total_games
    print(f"\nTotal Games: {total_games}")
    print(f"League Avg F5 Runs/Game: {league_avg_runs:.2f}\n")
    
    blended_factors = {}
    
    for venue, stats in venue_stats.items():
        if stats['games'] < 5:
            continue
            
        avg_runs = stats['runs'] / stats['games']
        realized_pf = avg_runs / league_avg_runs
        
        is_temporary = venue in ["Sutter Health Park", "Las Vegas Ballpark"]
        
        # We temporarily disable dynamic loading to just get the static baseline
        global _dynamic_pf_loaded
        import park_factors as pf_module
        pf_module._dynamic_pf_loaded = True 
        static_pf = pf_module.get_park_factor(venue)
        
        # If it returned 1.00 exactly AND it's not a known neutral park, it might be unmatched, 
        # but getting the actual static baseline is what matters.
        # A better check is if it's in the dict directly or matched via fuzzy.
        has_historical_baseline = not is_temporary
        
        if has_historical_baseline:
            blended_pf = (realized_pf * 0.15) + (static_pf * 0.85)
        else:
            if venue == "Sutter Health Park":
                blended_pf = (realized_pf * 0.50) + (1.000 * 0.50)
            elif venue == "Las Vegas Ballpark":
                blended_pf = min(realized_pf, 1.250)
            else:
                blended_pf = 1.00
                
        blended_factors[venue] = {
            "blended": round(blended_pf, 3),
            "static": round(static_pf, 3),
            "realized": round(realized_pf, 3)
        }
        print(f"{venue:30} | {stats['games']:3d} G | {avg_runs:.2f} R | Realized: {realized_pf:.3f} | Static: {static_pf:.3f} | Blended: {blended_pf:.3f}")

    out_path = os.path.join(os.path.dirname(__file__), 'Current_Blended_F5_PF.json')
    with open(out_path, 'w') as f:
        json.dump(blended_factors, f, indent=4)
    print(f"\nSaved Blended F5 Park Factors to {out_path}")

if __name__ == '__main__':
    main()
