import pandas as pd
from pybaseball import statcast_pitcher
from datetime import datetime
import os
import json

# 3-Year True Talent Weighting Configuration
YEAR_WEIGHTS = {2026: 0.50, 2025: 0.35, 2024: 0.15}

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')

def get_league_baseline_profile() -> dict:
    return {
        "bb_rate": 0.085,
        "k_rate": 0.225,
        "gb_rate": 0.43,
        "ld_rate": 0.25,
        "iffb_rate": 0.07,
        "offb_rate": 0.25,
        "hr_fb_rate": 0.125
    }

def fetch_and_profile_pitcher(player_id: int) -> dict:
    """
    Fetches multi-year Statcast data for a pitcher, aggregates plate appearance 
    outcomes and batted ball types, and returns a stabilized True Talent profile.
    """
    if not player_id:
        return get_league_baseline_profile()
        
    cache_path = os.path.join(CACHE_DIR, f"pitcher_bb_{player_id}_2026.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    yearly_profiles = {}
    
    # 1. Fetch and aggregate historical seasons
    for year, weight in YEAR_WEIGHTS.items():
        start_date = f"{year}-03-25"
        end_date = f"{year}-11-05"
        
        try:
            df = statcast_pitcher(start_date, end_date, player_id)
            if df.empty:
                continue
                
            # Filter to tracking-level events that conclude a plate appearance
            pa_df = df[df['events'].notna() & (df['events'] != '')]
            total_pas = len(pa_df)
            if total_pas == 0:
                continue
                
            # Tier 1 Event Aggregations
            walks = len(pa_df[pa_df['events'].isin(['walk', 'intent_walk', 'hit_by_pitch'])])
            strikeouts = len(pa_df[pa_df['events'] == 'strikeout'])
            
            # Tier 2 Batted Ball Aggregations (Only on valid batted balls)
            bb_df = pa_df[pa_df['bb_type'].notna() & (pa_df['bb_type'] != '')]
            total_bbs = len(bb_df)
            
            if total_bbs > 0:
                gb = len(bb_df[bb_df['bb_type'] == 'ground_ball'])
                ld = len(bb_df[bb_df['bb_type'] == 'line_drive'])
                iffb = len(bb_df[bb_df['bb_type'] == 'popup'])
                offb = len(bb_df[bb_df['bb_type'] == 'fly_ball'])
                
                # Normalize out home runs to extract pure actual HR/FB for Tier 3 stabilization
                hrs = len(bb_df[bb_df['events'] == 'home_run'])
                hr_fb_rate = hrs / offb if offb > 0 else 0.125
            else:
                gb, ld, iffb, offb, hr_fb_rate = 0, 0, 0, 0, 0.125

            yearly_profiles[year] = {
                "bb_rate": walks / total_pas,
                "k_rate": strikeouts / total_pas,
                "gb_rate": gb / total_bbs if total_bbs > 0 else 0.43,
                "ld_rate": ld / total_bbs if total_bbs > 0 else 0.25,
                "iffb_rate": iffb / total_bbs if total_bbs > 0 else 0.07,
                "offb_rate": offb / total_bbs if total_bbs > 0 else 0.25,
                "hr_fb_rate": hr_fb_rate
            }
        except Exception as e:
            # Continue if year fails
            continue

    # 2. Blend the profiles using normalized weights
    blended = blend_yearly_profiles(yearly_profiles)
    
    # Cache result
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(blended, f)
    except Exception:
        pass
        
    return blended

def blend_yearly_profiles(profiles: dict) -> dict:
    """Blends available seasons using available proportions if a player missed a year."""
    if not profiles:
        return get_league_baseline_profile()
        
    total_weight_present = sum(YEAR_WEIGHTS[yr] for yr in profiles.keys())
    blended = {k: 0.0 for k in ["bb_rate", "k_rate", "gb_rate", "ld_rate", "iffb_rate", "offb_rate", "hr_fb_rate"]}
    
    for year, data in profiles.items():
        normalized_weight = YEAR_WEIGHTS[year] / total_weight_present
        for stat in blended.keys():
            blended[stat] += data[stat] * normalized_weight
            
    return blended
