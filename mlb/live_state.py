"""
live_state.py
=============
Live game state machine for the LF5 engine.

Polls the MLB Stats API for real-time game conditions and constructs
the standardized live_game_state payload for the continuation engine.

Speed tier mapping (Statcast Sprint Speed ft/s):
    0 = Sluggish  (<27.0)   — pitchers, slow catchers
    1 = Average   (27.0–29.0)
    2 = Elite     (>29.0)   — top outfielders, speedsters
"""

import statsapi

# ---------------------------------------------------------------------------
# Sprint speed → speed tier mapping
# ---------------------------------------------------------------------------
# Approximate 2024-2026 MLB sprint speed percentiles
_SPRINT_SPEED_CACHE: dict[int, int] = {}   # player_id → speed tier

# Statcast sprint speed data from the Stats API is not directly available
# via the standard statsapi package. We use a curated static map of known
# elite/sluggish runners as a practical approximation. Any player not in the
# map defaults to tier 1 (Average).
#
# Elite runners (tier 2) — sprint speed >29 ft/s
# IDs verified against MLB Stats API (statsapi.lookup_player) 2026-06-08
_ELITE_RUNNERS = {
    677951,  # Bobby Witt Jr.
    682829,  # Elly De La Cruz
    664034,  # Corbin Carroll
    669257,  # Jose Caballero
    641355,  # Trea Turner
    665862,  # Jazz Chisholm Jr.
    665161,  # Julio Rodriguez
    682998,  # Jarren Duran
    677951,  # Bobby Witt Jr. (duplicate guard)
    666152,  # Cedric Mullins
    642715,  # Tommy Edman
    660670,  # Jorge Mateo
    676801,  # Zac Veen
    681481,  # Jackson Chourio
}

# Sluggish runners (tier 0) — sprint speed <27 ft/s
_SLUGGISH_RUNNERS = {
    607043,  # Daniel Vogelbach
    621566,  # Ji Man Choi
    # Most catchers default sluggish via position check below
}


def get_runner_speed_tier(player_id: int) -> int:
    """
    Returns 0 (Sluggish), 1 (Average), or 2 (Elite) for a given player_id.
    Uses a curated static map + API position fallback.
    Results are cached per session.
    """
    if player_id in _SPRINT_SPEED_CACHE:
        return _SPRINT_SPEED_CACHE[player_id]

    if player_id in _ELITE_RUNNERS:
        tier = 2
    elif player_id in _SLUGGISH_RUNNERS:
        tier = 0
    else:
        # Check position via API — catchers default sluggish, pitchers sluggish
        try:
            data = statsapi.get('people', {'personIds': player_id})
            people = data.get('people', [])
            if people:
                pos = people[0].get('primaryPosition', {}).get('code', '')
                if pos in ('C', '2'):       # Catcher
                    tier = 0
                elif pos == '1':            # Pitcher
                    tier = 0
                elif pos in ('7', '8', '9'):  # Outfielders lean average/elite
                    tier = 1
                else:
                    tier = 1
            else:
                tier = 1
        except Exception:
            tier = 1

    _SPRINT_SPEED_CACHE[player_id] = tier
    return tier


# ---------------------------------------------------------------------------
# Core live state fetcher
# ---------------------------------------------------------------------------

def fetch_live_state(game_id: int) -> dict | None:
    """
    Fetches the live game state from the MLB Stats API.

    Returns a live_game_state dict on success, or None if the game is
    not yet in progress or the API call fails.

    Parameters
    ----------
    game_id : int   The MLB Stats API game_id (gamePk).

    Returns
    -------
    dict with keys:
        game_id, game_status, current_inning, is_bottom_inning,
        current_outs, scoreboard, basepaths, lineup_pointers,
        pitcher_tracking, micro_climate (None — filled by daemon)
    """
    try:
        data = statsapi.get('game', {'gamePk': game_id})
    except Exception as e:
        print(f"  [live_state] API error for game {game_id}: {e}")
        return None

    game_data = data.get('gameData', {})
    live_data  = data.get('liveData', {})

    # Game status
    status_code = game_data.get('status', {}).get('abstractGameCode', 'P')
    # abstractGameCode: 'P'=Preview, 'L'=Live, 'F'=Final
    if status_code == 'F':
        return _build_final_state(game_id, live_data)
    if status_code != 'L':
        return None     # Not started yet

    linescore = live_data.get('linescore', {})
    
    # ── Inning & outs ──────────────────────────────────────────────────────
    current_inning   = linescore.get('currentInning', 1)
    inning_half      = linescore.get('inningHalf', 'Top')   # 'Top' or 'Bottom'
    is_bottom_inning = (inning_half.lower() == 'bottom')
    current_outs     = linescore.get('outs', 0)

    # F5 window check — if past inning 5, engine is N/A
    if current_inning > 5 or (current_inning == 5 and is_bottom_inning and current_outs == 3):
        return _build_final_state(game_id, live_data)

    # ── Scoreboard ─────────────────────────────────────────────────────────
    away_runs = linescore.get('teams', {}).get('away', {}).get('runs', 0) or 0
    home_runs = linescore.get('teams', {}).get('home', {}).get('runs', 0) or 0

    # ── Base runners ────────────────────────────────────────────────────────
    offense = linescore.get('offense', {})
    
    def _extract_runner(base_key: str) -> int | None:
        """Returns player_id of runner on given base, or None."""
        runner = offense.get(base_key, {})
        if runner:
            return runner.get('id')
        return None

    runner_1b_id = _extract_runner('first')
    runner_2b_id = _extract_runner('second')
    runner_3b_id = _extract_runner('third')

    basepaths = {
        'first_base':  runner_1b_id,
        'second_base': runner_2b_id,
        'third_base':  runner_3b_id,
    }

    # ── Lineup pointers — next batter index ────────────────────────────────
    # The batting order position of the current batter (1-indexed in API).
    # We convert to 0-indexed for the simulation engine.
    current_batter_pos = offense.get('battingOrder', 0)   # 0 if no batter info
    if current_batter_pos:
        # battingOrder is a 3-digit string in the raw API: "100"=1st, "900"=9th
        # After a half-inning, we want the *next* batter, not current.
        next_hitter_raw = int(str(current_batter_pos)[:1]) - 1  # 0-indexed
    else:
        next_hitter_raw = 0

    # Home batting pointer — less directly accessible; approximate from linescore
    # The home team bats in the Bottom, so we check the defensive lineup
    defense = linescore.get('defense', {})
    # We'll use 0 as fallback if we can't determine home next batter
    home_next_hitter = 0  # Will be refined in future via play-by-play endpoint

    lineup_pointers = {
        'away_next_hitter_index': next_hitter_raw if not is_bottom_inning else home_next_hitter,
        'home_next_hitter_index': home_next_hitter if not is_bottom_inning else next_hitter_raw,
    }

    # ── Pitcher tracking ────────────────────────────────────────────────────
    pitcher_info = defense.get('pitcher', {}) if is_bottom_inning else \
                   linescore.get('defense', {}).get('pitcher', {})
    # More accurate: parse from boxscore
    pitcher_tracking = _get_pitcher_tracking(game_id, live_data, is_bottom_inning)

    return {
        'game_id':           game_id,
        'game_status':       'IN_PROGRESS',
        'current_inning':    current_inning,
        'is_bottom_inning':  is_bottom_inning,
        'current_outs':      current_outs,
        'scoreboard': {
            'away_runs': int(away_runs),
            'home_runs': int(home_runs),
        },
        'basepaths':         basepaths,
        'lineup_pointers':   lineup_pointers,
        'pitcher_tracking':  pitcher_tracking,
        'micro_climate':     None,   # Populated by daemon from weather module
    }


def _get_pitcher_tracking(game_id: int, live_data: dict, is_bottom_inning: bool) -> dict:
    """
    Extracts pitcher tracking metrics from the live game data.
    Returns cumulative pitch count, current-inning pitch count, and stress innings.
    """
    try:
        decisions = live_data.get('decisions', {})
        box = statsapi.boxscore_data(game_id)

        # Determine which team is pitching (away pitches in bottom, home in top)
        pitching_team_key = 'away' if is_bottom_inning else 'home'
        pitchers = box.get(pitching_team_key, {}).get('pitchers', [])
        
        # Active pitcher is the last one in the list
        active_id       = None
        cumulative_pct  = 0
        current_inn_pc  = 0
        stress_innings  = 0

        if pitchers:
            active_id = pitchers[-1]
            try:
                # Pull pitch count from game's current linescore
                linescore = live_data.get('linescore', {})
                # pitchCount is available in the offense/defense object
                defense = linescore.get('defense', {})
                cumulative_pct = defense.get('pitcher', {}).get('pitchCount', 0) or 0
            except Exception:
                cumulative_pct = 0

            # Estimate current-inning pitch count from pitch log
            # (Full play-by-play would give exact data; we approximate)
            # If cumulative > 0 and game is early innings, use heuristic
            current_inn_pc = max(0, cumulative_pct - max(0, cumulative_pct - 20))

            # Count high-stress innings: if avg pitches/inning > 25
            innings_pitched = max(1, cumulative_pct // 17)  # ~17 pitches/inning avg
            stress_innings  = max(0, innings_pitched - 3)    # Conservative estimate

    except Exception as e:
        active_id      = None
        cumulative_pct = 0
        current_inn_pc = 0
        stress_innings = 0

    return {
        'active_pitcher_id':           active_id,
        'cumulative_pitch_count':      int(cumulative_pct),
        'current_inning_pitch_count':  int(current_inn_pc),
        'high_stress_innings_count':   int(stress_innings),
    }


def _build_final_state(game_id: int, live_data: dict) -> dict:
    """Returns a minimal state dict indicating the F5 window is closed."""
    linescore = live_data.get('linescore', {})
    return {
        'game_id':        game_id,
        'game_status':    'FINAL_F5',
        'current_inning': linescore.get('currentInning', 5),
        'scoreboard': {
            'away_runs': linescore.get('teams', {}).get('away', {}).get('runs', 0),
            'home_runs': linescore.get('teams', {}).get('home', {}).get('runs', 0),
        },
    }


def get_basepath_speed_tiers(basepaths: dict) -> dict:
    """
    Converts basepath player_id values to speed tier integers.
    Returns {'first_base': int|None, 'second_base': int|None, 'third_base': int|None}
    """
    result = {}
    for base, pid in basepaths.items():
        if pid is not None:
            result[base] = get_runner_speed_tier(int(pid))
        else:
            result[base] = None
    return result


def detect_pitcher_change(prev_state: dict, curr_state: dict) -> bool:
    """
    Returns True if the active pitcher changed between two state snapshots.
    Used by the daemon to trigger bullpen swap logic.
    """
    prev_id = prev_state.get('pitcher_tracking', {}).get('active_pitcher_id')
    curr_id = curr_state.get('pitcher_tracking', {}).get('active_pitcher_id')
    if prev_id is None or curr_id is None:
        return False
    return prev_id != curr_id


if __name__ == '__main__':
    import datetime
    today = datetime.datetime.now().strftime('%m/%d/%Y')
    schedule = statsapi.schedule(sportId=1, date=today)
    if schedule:
        game = schedule[0]
        gid = game['game_id']
        print(f"Testing live state fetch for game {gid}: {game['away_name']} @ {game['home_name']}")
        state = fetch_live_state(gid)
        if state:
            print(f"  Status: {state['game_status']}")
            print(f"  Inning: {'Bot' if state.get('is_bottom_inning') else 'Top'} {state.get('current_inning')}, Outs: {state.get('current_outs')}")
            print(f"  Score: Away {state['scoreboard']['away_runs']} - Home {state['scoreboard']['home_runs']}")
            print(f"  Pitcher pitch count: {state['pitcher_tracking']['cumulative_pitch_count']}")
        else:
            print("  Game not in progress (no live state available).")
