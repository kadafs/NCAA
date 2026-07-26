import pybaseball
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Enable pybaseball caching to avoid hitting rate limits or slow queries repeatedly
pybaseball.cache.enable()

def get_pitcher_first_inning_stats(mlbam_id, start_date='2026-03-20', end_date=None):
    """
    Fetches the starting pitcher's exact performance specifically in the 1st inning
    using Statcast pitch-by-pitch data.
    """
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        
    try:
        data = pybaseball.statcast_pitcher(start_date, end_date, player_id=mlbam_id)
        if data is None or data.empty:
            return None
            
        first_inning = data[data['inning'] == 1]
        if first_inning.empty:
            return None
            
        # Calculate xwOBA in the 1st inning
        xwoba_events = first_inning.dropna(subset=['events', 'estimated_woba_using_speedangle'])
        if not xwoba_events.empty:
            xwoba = xwoba_events['estimated_woba_using_speedangle'].mean()
        else:
            xwoba = 0.320 # league average fallback
            
        # K% and BB% in the 1st inning
        events_only = first_inning.dropna(subset=['events'])
        total_batters = len(events_only)
        
        if total_batters > 0:
            k_pct = len(events_only[events_only['events'] == 'strikeout']) / total_batters
            bb_pct = len(events_only[events_only['events'].isin(['walk', 'hit_by_pitch'])]) / total_batters
        else:
            k_pct = 0.22
            bb_pct = 0.08
            
        return {
            'xwoba_1st': round(xwoba, 3),
            'k_pct_1st': round(k_pct, 3),
            'bb_pct_1st': round(bb_pct, 3),
            'total_bf_1st': total_batters
        }
        
    except Exception as e:
        print(f"Error fetching 1st inning stats for {mlbam_id}: {e}")
        return None

def get_batter_xwoba_vs_hand(mlbam_id, p_throws, start_date='2026-03-20', end_date=None):
    """
    Fetches a specific batter's performance vs a specific pitcher handedness (L or R).
    """
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        
    try:
        data = pybaseball.statcast_batter(start_date, end_date, player_id=mlbam_id)
        if data is None or data.empty:
            return None
            
        # Filter by pitcher handedness
        vs_hand = data[data['p_throws'] == p_throws]
        if vs_hand.empty:
            return None
            
        # Calculate xwOBA
        xwoba_events = vs_hand.dropna(subset=['events', 'estimated_woba_using_speedangle'])
        if not xwoba_events.empty:
            xwoba = xwoba_events['estimated_woba_using_speedangle'].mean()
        else:
            xwoba = 0.320 # league average fallback
            
        return {
            'xwoba_vs_hand': round(xwoba, 3),
            'total_events': len(xwoba_events)
        }
        
    except Exception as e:
        print(f"Error fetching batter stats for {mlbam_id}: {e}")
        return None

if __name__ == "__main__":
    # Test Tarik Skubal (LHP) 1st Inning stats
    print("Testing Skubal 1st Inning:")
    print(get_pitcher_first_inning_stats(669373))
    
    # Test Aaron Judge vs LHP
    print("\nTesting Aaron Judge vs LHP:")
    print(get_batter_xwoba_vs_hand(592450, 'L'))
