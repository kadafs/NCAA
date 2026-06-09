"""
live_f5.py
==========
The main CLI runner and background daemon for the LF5 Live Inning Engine.

Continuously polls active MLB games every 30 seconds during the F5 window.
Uses The Odds API to fetch live sports betting lines, runs the vectorized
continuation engine, and detects actionable mathematical edges > 4.5%.
"""

import os
import sys
import time
import datetime
import argparse
import requests
from requests.exceptions import RequestException

# ---------------------------------------------------------------------------
# Windows UTF-8 Fix: Force stdout to UTF-8 to prevent emoji UnicodeEncodeError
# This is critical — without this, the daemon crashes the moment it fires an
# alert containing emoji characters on Windows terminals using CP1252 encoding.
# ---------------------------------------------------------------------------
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from live_cache import build_morning_cache, save_cache, load_cache, CACHE_DIR
from live_state import fetch_live_state
from live_engine import run_live_simulation
from live_modifiers import (
    get_bullpen_availability, FATIGUE_THRESHOLD, calc_fatigue_scaler
)
from weather_f5 import get_weather_modifier

# ---------------------------------------------------------------------------
# The Odds API Integration
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    # Load from the parent directory where .env is stored
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
except ImportError:
    pass

# Requires an API key from https://the-odds-api.com/
# Set it in your environment or .env file
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")

def fetch_live_odds() -> dict:
    """
    Fetches live MLB alternative totals for the First 5 Innings (if available)
    or full game totals from The Odds API.
    
    Returns a dict mapping "AwayTeam@HomeTeam" -> {'line': 4.5, 'over_odds': -110, 'under_odds': -110}
    """
    if not ODDS_API_KEY:
        return {}
        
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'totals', # 'alternate_totals' requires higher API tier
        'oddsFormat': 'american'
    }
    
    odds_map = {}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for event in data:
                home = event.get('home_team')
                away = event.get('away_team')
                # Parse team names to 2-3 letter abbreviations to match our keys,
                # or just use full names if we normalize them.
                # For this demo, we'll use full team names mapped.
                key = f"{away}@{home}"
                
                # Find the best totals line from a sharp book (e.g., Pinnacle or DraftKings)
                for bookmaker in event.get('bookmakers', []):
                    if bookmaker.get('key') in ('draftkings', 'pinnacle', 'fanduel'):
                        for market in bookmaker.get('markets', []):
                            if market.get('key') == 'totals':
                                outcomes = market.get('outcomes', [])
                                if len(outcomes) == 2:
                                    o1, o2 = outcomes[0], outcomes[1]
                                    if o1.get('name') == 'Over':
                                        over, under = o1, o2
                                    else:
                                        over, under = o2, o1
                                        
                                    odds_map[key] = {
                                        'line': over.get('point'),
                                        'over_odds': over.get('price'),
                                        'under_odds': under.get('price')
                                    }
                                break # Use first sharp book found
                        break
    except RequestException as e:
        print(f"  [OddsAPI] Failed to fetch live odds: {e}")
        
    return odds_map


def american_to_implied(raw_odds_input) -> float:
    """
    Sanitizes, type-casts, and converts raw sportsbook odds strings/integers
    into standard implied probabilities, preventing mid-game runtime failures.

    Handles:
      - Integers      (-110, 120)
      - Signed strings ('-110', '+120')
      - Pick'em values (100, -100)
      - Edge case: '+' stripped before cast so ''+120" -> 120 -> correct branch

    Returns 0.5 (neutral pick'em) on any unparseable input.
    """
    try:
        # Step 1: Force to string, strip whitespace and explicit positive signs
        clean_string = str(raw_odds_input).replace('+', '').strip()

        # Step 2: Safe cast to a standard signed integer
        odds_integer = int(clean_string)

        # Step 3: Branch routing based on sign
        if odds_integer < 0:
            # Minus Odds: e.g. -110 -> 110 / (110 + 100) = 52.38%
            return abs(odds_integer) / (abs(odds_integer) + 100.0)
        else:
            # Plus Odds: e.g. +120 -> 100 / (120 + 100) = 45.45%
            # Also handles 100 (pick'em) correctly: 100 / 200 = 50.0%
            return 100.0 / (odds_integer + 100.0)

    except (ValueError, TypeError) as error:
        print(f"  [OddsAPI] WARN: Failed to parse odds payload '{raw_odds_input}': {error}")
        return 0.5000  # Default to neutral pick'em to prevent simulation halting


def calculate_edge(model_prob: float, implied_prob: float) -> dict | None:
    """
    Checks if the absolute variance between the Model Probability 
    and the Bookmaker Implied Probability exceeds 4.5%.
    """
    variance = model_prob - implied_prob
    if abs(variance) >= 0.045:
        return {
            'edge_pct': round(variance * 100, 2),
            'confidence': 'HIGH' if abs(variance) >= 0.07 else 'MODERATE'
        }
    return None

# ---------------------------------------------------------------------------
# Daemon Logic
# ---------------------------------------------------------------------------

def run_daemon(sport_id: int = 1, interval_sec: int = 30, test_mode: bool = False):
    """
    The main LF5 polling daemon.
    """
    print("=========================================================")
    print(" LF5 Live Engine Daemon Started")
    print("=========================================================")
    
    # 1. Load or build morning cache
    today_str = (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%Y-%m-%d")
    cache_path = os.path.join(CACHE_DIR, f"lf5_cache_{today_str}.npz")
    
    cache = load_cache(cache_path)
    if not cache:
        cache = build_morning_cache(sport_id)
        if cache:
            save_cache(cache)
    
    if not cache:
        print("Failed to initialize morning cache. Exiting.")
        return
        
    print(f"Loaded morning cache for {len(cache)} games. Monitoring...")
    print(f"Polling interval: {interval_sec}s. Press Ctrl+C to stop.\n")
    
    # Track games we've processed as FINAL_F5 so we stop polling them
    finalized_games = set()

    # Per-game live weather cache: refreshed every ~5 minutes (10 poll cycles)
    # Avoids hammering wttr.in on every 30-second poll
    live_weather_cache: dict[str, dict] = {}
    weather_refresh_counter: dict[str, int] = {}
    WEATHER_REFRESH_EVERY = 10  # polls (~5 min at 30s interval)

    # Per-game bullpen availability cache: refreshed every ~15 minutes (30 polls)
    # get_bullpen_availability hits the Stats API per pitcher — expensive to call every 30s
    bullpen_cache: dict[str, dict] = {}
    bullpen_refresh_counter: dict[str, int] = {}
    BULLPEN_REFRESH_EVERY = 30

    try:
        while True:
            # 2. Fetch Live Odds
            live_odds = fetch_live_odds()
            
            # 3. Poll active games
            for gid_str, game_cache in cache.items():
                if gid_str in finalized_games:
                    continue

                gid = int(gid_str)
                state = fetch_live_state(gid)

                if not state:
                    continue  # Not started or API error

                if state['game_status'] == 'FINAL_F5':
                    finalized_games.add(gid_str)
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Game {gid} F5 window closed. Stop monitoring.")
                    continue

                # ── Live Weather Injection (micro_climate) ───────────────────
                # fetch_live_state() returns micro_climate=None.
                # We populate it here from wttr.in (live GPS weather at the stadium)
                # so the fatigue scaler's temp component, crosswind modifier, and
                # wind-shift detector all receive real in-play conditions.
                weather_refresh_counter[gid_str] = weather_refresh_counter.get(gid_str, WEATHER_REFRESH_EVERY)
                if weather_refresh_counter[gid_str] >= WEATHER_REFRESH_EVERY:
                    venue        = game_cache.get('morning_weather', {}).get('venue', '')
                    away_abbr    = game_cache.get('away_team_name', '')[:3].upper()
                    home_abbr    = game_cache.get('home_team_name', '')[:3].upper()
                    wx = get_weather_modifier(venue, away_abbr, home_abbr)
                    live_weather_cache[gid_str] = {
                        'live_temp':        wx.get('temp', 72),
                        'live_wind_dir':    wx.get('wind_lateral') or wx.get('wind_dir', 'CALM'),
                        'live_wind_speed':  wx.get('wind_mph', 0),
                    }
                    weather_refresh_counter[gid_str] = 0
                else:
                    weather_refresh_counter[gid_str] += 1

                state['micro_climate'] = live_weather_cache.get(gid_str, {
                    'live_temp': 72, 'live_wind_dir': 'CALM', 'live_wind_speed': 0
                })

                # ── Bullpen Availability Cache ────────────────────────────────
                bullpen_refresh_counter[gid_str] = bullpen_refresh_counter.get(gid_str, BULLPEN_REFRESH_EVERY)
                if bullpen_refresh_counter[gid_str] >= BULLPEN_REFRESH_EVERY:
                    away_team = game_cache.get('away_team_name', '')
                    home_team = game_cache.get('home_team_name', '')
                    bullpen_cache[gid_str] = {
                        'away': get_bullpen_availability(away_team),
                        'home': get_bullpen_availability(home_team),
                    }
                    bullpen_refresh_counter[gid_str] = 0
                else:
                    bullpen_refresh_counter[gid_str] += 1

                # 4. Run LF5 Engine
                res = run_live_simulation(state, game_cache)

                # Calculate Fatigue for logging
                cum_pitches = state['pitcher_tracking']['cumulative_pitch_count']
                stress_inns = state['pitcher_tracking']['high_stress_innings_count']
                live_temp   = state['micro_climate']['live_temp']
                fatigue     = calc_fatigue_scaler(cum_pitches, stress_inns, live_temp)
                
                # 5. Check Odds for Edges
                away_team = game_cache.get('away_team_name')
                home_team = game_cache.get('home_team_name')
                odds_key = f"{away_team}@{home_team}"
                
                # If we don't have The Odds API, we simulate a line check for testing
                if test_mode and not live_odds:
                    # Dummy line based on projected total
                    line = round(res['projected_f5_total'] * 2) / 2
                    line = max(3.5, line)
                    live_odds[odds_key] = {'line': line, 'over_odds': -110, 'under_odds': -110}
                
                game_odds = live_odds.get(odds_key)
                
                if game_odds:
                    line = game_odds['line']
                    
                    # Odds API fallback: If the API returns a Full Game total (e.g. 8.5) 
                    # we must heuristically convert it to an F5 line to match our F5 engine.
                    # MLB F5 lines are typically ~54% of the full game total.
                    if line >= 6.5:
                        converted_line = round((line * 0.54) * 2) / 2
                        # Ensure we don't drop below the minimum F5 line offered by books
                        line = max(3.5, converted_line)
                        
                    under_prob = res['under_line_prob'].get(line)
                    
                    if under_prob is not None:
                        over_prob = 1.0 - under_prob
                        
                        under_implied = american_to_implied(game_odds['under_odds'])
                        over_implied  = american_to_implied(game_odds['over_odds'])
                        
                        under_edge = calculate_edge(under_prob, under_implied)
                        over_edge  = calculate_edge(over_prob, over_implied)
                        
                        if under_edge or over_edge:
                            _log_edge(away_team, home_team, state, res, line, game_odds, 
                                      under_prob, over_prob, under_implied, over_implied, 
                                      under_edge, over_edge, fatigue)
            
            if test_mode:
                break
                
            time.sleep(interval_sec)
            
    except KeyboardInterrupt:
        print("\nDaemon stopped by user.")


def _safe_print(text: str):
    """Prints text, replacing any unencodable characters to prevent crashes."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))


def _log_edge(away_team, home_team, state, res, line, odds, under_p, over_p, under_imp, over_imp, under_edge, over_edge, fatigue):
    """Formats and prints an actionable trading alert."""
    ts = datetime.datetime.now().strftime('%H:%M:%S')
    inn_str = f"{'Bot' if state['is_bottom_inning'] else 'Top'} {state['current_inning']}"
    outs = state['current_outs']
    score = f"{away_team} {state['scoreboard']['away_runs']} - {state['scoreboard']['home_runs']} {home_team}"
    
    _safe_print(f"\n[{ts}] \U0001f6a8 LF5 EDGE DETECTED \U0001f6a8")
    _safe_print(f"  Game:  {score} ({inn_str}, {outs} Outs)")
    
    if fatigue > FATIGUE_THRESHOLD:
        _safe_print(f"  \u26a0\ufe0f PITCHER FATIGUE ALERT: Scaler = {fatigue:.2f} (>1.10)")
        
    _safe_print(f"  Proj Total: {res['projected_f5_total']} (Remaining: {res['remaining_away_runs'] + res['remaining_home_runs']})")
    
    if over_edge:
        _safe_print(f"  \U0001f3af BET OVER {line}  ({odds['over_odds']})")
        _safe_print(f"     Model Over Prob: {over_p*100:.1f}% vs Book Implied: {over_imp*100:.1f}%")
        _safe_print(f"     Edge: +{over_edge['edge_pct']}%  Confidence: {over_edge['confidence']}")
        
    if under_edge:
        _safe_print(f"  \U0001f3af BET UNDER {line} ({odds['under_odds']})")
        _safe_print(f"     Model Under Prob: {under_p*100:.1f}% vs Book Implied: {under_imp*100:.1f}%")
        _safe_print(f"     Edge: +{under_edge['edge_pct']}%  Confidence: {under_edge['confidence']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="LF5 Live Inning Engine Daemon")
    parser.add_argument('--test', action='store_true', help='Run one loop with dummy odds for testing')
    parser.add_argument('--interval', type=int, default=30, help='Polling interval in seconds')
    args = parser.parse_args()
    
    run_daemon(interval_sec=args.interval, test_mode=args.test)
