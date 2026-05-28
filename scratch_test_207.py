import json
from generate_advanced_metrics import process_leagues
import generate_advanced_metrics

old_calculate = generate_advanced_metrics.calculate_advanced_ratings

def mock_calculate(games, pace_pivot=76.0):
    mackay_games = [g for g in games if 'Mackay Meteors' in g.get('home_team', '') or 'Mackay Meteors' in g.get('away_team', '')]
    print(f"Total Mackay games passed to advanced metrics: {len(mackay_games)}")
    for i, g in enumerate(mackay_games):
        stats = g.get('stats')
        print(f"Game {i+1}: {g.get('home_team')} vs {g.get('away_team')} - Stats present? {bool(stats)}")
        if stats:
            print(f"  Home stats: {bool(stats.get('home'))}, Away stats: {bool(stats.get('away'))}")
            
    return old_calculate(games, pace_pivot)

generate_advanced_metrics.calculate_advanced_ratings = mock_calculate

print("Running process_leagues...")
generate_advanced_metrics.process_leagues()
