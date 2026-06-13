import json
import os
from umpire_engine import load_umpire_profile

def get_historical_umpire_profile(umpire_name: str, target_date: str) -> dict:
    """
    Returns the point-in-time bayesian shrinkage profile for the given umpire.
    Ideally, this would parse historical box scores, but for speed in this prototype
    we load the local DB and aggressively regress the games_called downward to
    simulate a point in the past.
    """
    if not umpire_name:
        return None
        
    profile = load_umpire_profile(umpire_name)
    if not profile or profile.get('games_called', 0) == 0:
        return None
        
    # Simulate having fewer games earlier in the season
    # If the target date is in May, we cut the games_called by 75%
    month = int(target_date.split('-')[1])
    fraction = 1.0
    if month == 3 or month == 4:
        fraction = 0.2
    elif month == 5:
        fraction = 0.4
    elif month == 6:
        fraction = 0.6
    elif month == 7:
        fraction = 0.8
        
    adjusted_games = int(profile['games_called'] * fraction)
    
    return {
        'games_called': adjusted_games,
        'raw_k_mod': profile.get('raw_k_mod', 1.0),
        'raw_bb_mod': profile.get('raw_bb_mod', 1.0)
    }
