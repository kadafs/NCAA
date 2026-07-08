"""
grade_td_reports.py
===================
Grades the existing markdown reports based on:
  1. "Top-Down Projected F5 Total" vs a specific F5 line (e.g., 4.5)
  2. "Full Game Probs" (Over 7.5 / 8.5 / 9.5) — graded against the actual full game total.
It does not re-run the model, making it incredibly fast.

Usage:
    python mlb/grade_td_reports.py                          # grades MLB against 4.5
    python mlb/grade_td_reports.py --sportId 11             # grades AAA against 4.5
    python mlb/grade_td_reports.py --line 5.5               # grades against 5.5
    python mlb/grade_td_reports.py --no-fg                  # skip Full Game grading
"""
import time
import os, re, sys, argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import statsapi

# ---------------------------------------------------------------------------
# Report file map
# ---------------------------------------------------------------------------
def get_report_filepath(sport_id, schedule_date):
    # Convert schedule_date (MM/DD/YYYY) to report date format (YYYY-MM-DD)
    try:
        report_date = datetime.strptime(schedule_date, '%m/%d/%Y').strftime('%Y-%m-%d')
    except ValueError:
        report_date = schedule_date

    if sport_id == 1:
        filename = f"consensus_f5_v3_report_{report_date}.md"
    elif sport_id == 11:
        filename = f"consensus_f5_v3_report_AAA_{report_date}.md"
    elif sport_id == 12:
        filename = f"consensus_f5_v3_report_AA_{report_date}.md"
    else:
        filename = f"consensus_f5_v3_report_{sport_id}_{report_date}.md"
        
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

SPORT_LABELS = {1: 'MLB', 11: 'AAA', 12: 'AA'}


# ---------------------------------------------------------------------------
# Report parser
# ---------------------------------------------------------------------------
def parse_report(filepath, line=4.5, grading_mode='fixed'):
    """
    Parses a markdown report and extracts the Top-Down projection and Full Game Probs.
    Returns a list of dicts:
      {
        'matchup': ...,
        'game_line': ...,
        'action_raw': ...,
        'action_bet': ...,
        'fg_line_for_over': ...,
        'fg_over_7_5': ...,
        'fg_over_8_5': ...,
        'fg_over_9_5': ...
      }
    """
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # --- Parse Gatekeeper V6 Recommendations (New Format) ---
    gatekeeper_actions = {}
    if '## Active Portfolio Recommendations' in content:
        try:
            gk_block = content.split('## Active Portfolio Recommendations')[1].split('---')[0]
            # Match: **Chicago White Sox @ Baltimore Orioles** ──► **BET F5 OVER**
            for m in re.finditer(r'\*\*(.*?)\*\*\s*──►\s*\*\*(.*?)\*\*', gk_block):
                gk_matchup = m.group(1).strip()
                gk_action = m.group(2).strip()
                gatekeeper_actions[gk_matchup] = gk_action
        except Exception:
            pass

    games = []
    blocks = re.split(r'\n(?=###\s)', content.strip())

    for block in blocks:
        if '### ' not in block:
            continue

        # --- Matchup name ---
        header_match = re.search(r'###\s+([^\n]+)', block)
        if not header_match:
            continue
        raw_header = header_match.group(1).strip()
        # strip out any weird unicode/emoji prefixes (like dYs") before the first letter
        raw_header = re.sub(r'^[^\w]+', '', raw_header).strip()
        matchup = re.sub(r'\s*\([^)]*\)', '', raw_header).strip()
        # Extract just the team vs team (strip out pitchers in parentheses for gatekeeper matching)
        matchup_clean_match = re.match(r'^(.*?)\s*\(.*?\)\s*@\s*(.*?)\s*\(.*?\)$', raw_header)
        if matchup_clean_match:
            matchup_teams = f"{matchup_clean_match.group(1).strip()} @ {matchup_clean_match.group(2).strip()}"
        else:
            matchup_teams = matchup

        # --- Top-Down Total ---
        td_match = re.search(r'-\s*\*\*Monte Carlo Simulated F5 Total:\*\*\s*(\d+\.?\d*)\s*Runs', block)
        td_total = float(td_match.group(1)) if td_match else None

        # --- Check Gatekeeper (v4 format) first ---
        gk_found_action = None
        for gk_matchup, act in gatekeeper_actions.items():
            if gk_matchup in matchup_teams:
                gk_found_action = act
                break
        
        if gk_found_action and grading_mode in ('fixed', 'all') and line == 4.5:
            game_line = 4.5
            action_raw = gk_found_action
            if "OVER" in action_raw:
                action_bet = "OVER"
            elif "UNDER" in action_raw:
                action_bet = "UNDER"
            else:
                action_bet = "SKIP"
        else:
            game_line = line
            action_raw = "Not Found / No Edge"
            action_bet = "SKIP"

        # --- Force Grade All Games (No Edge -> TD Forced) ---
        if grading_mode == 'all' and action_bet == "SKIP":
            if td_total is not None:
                if td_total > game_line:
                    action_bet = "OVER"
                    action_raw = f"Bet **OVER** (TD Forced: {td_total})"
                elif td_total < game_line:
                    action_bet = "UNDER"
                    action_raw = f"Bet **UNDER** (TD Forced: {td_total})"
                else:
                    action_bet = "SKIP"
                    action_raw = f"Skip (TD {td_total} == Line)"
            else:
                action_bet = "SKIP"
                action_raw = "TD Total Not Found"
        # Fallback for old legacy logic removed since Gatekeeper handles all formatting now.
        if grading_mode != 'all':
            if getattr(locals(), 'action_bet', None) is None:  # Might be set by Gatekeeper
                if "Skip" in action_raw or "Not Found" in action_raw:
                    action_bet = "SKIP"
                elif "UNDER" in action_raw:
                    action_bet = "UNDER"
                elif "FULL GAME OVER" in action_raw:
                    action_bet = "FG_OVER"
                elif "OVER" in action_raw:
                    action_bet = "OVER"
                else:
                    action_bet = "SKIP"

        fg_line_for_over = None
        if action_bet == "FG_OVER":
            m = re.search(r'\(e\.g\.\s*(\d+\.?\d*)\)', action_raw)
            if m:
                fg_line_for_over = float(m.group(1))

        # --- Parse Full Game Probs ---
        # Format: **Full Game Probs:** Over 7.5: 75% | Over 8.5: 63% | Over 9.5: 50%
        fg_match = re.search(
            r'\*\*?Full Game Probs:\*\*?\s*Over 7\.5:\s*(\d+)%\s*\|\s*Over 8\.5:\s*(\d+)%\s*\|\s*Over 9\.5:\s*(\d+)%',
            block
        )
        fg_over_7_5 = float(fg_match.group(1)) / 100 if fg_match else None
        fg_over_8_5 = float(fg_match.group(2)) / 100 if fg_match else None
        fg_over_9_5 = float(fg_match.group(3)) / 100 if fg_match else None

        games.append({
            'matchup':    matchup,
            'game_line':  game_line,
            'action_raw': action_raw,
            'action_bet': action_bet,
            'fg_line_for_over': fg_line_for_over,
            'fg_over_7_5': fg_over_7_5,
            'fg_over_8_5': fg_over_8_5,
            'fg_over_9_5': fg_over_9_5,
        })

    return games


# ---------------------------------------------------------------------------
# Match a parsed matchup name to a scheduled game
# ---------------------------------------------------------------------------
def find_game_id(matchup, schedule):
    if ' @ ' not in matchup:
        return None
    away_q, home_q = [t.strip().lower() for t in matchup.split(' @ ', 1)]

    for g in schedule:
        away_s = g['away_name'].lower()
        home_s = g['home_name'].lower()
        if away_q in away_s or away_s in away_q:
            if home_q in home_s or home_s in home_q:
                return g['game_id']
    return None


# ---------------------------------------------------------------------------
# Grade a single sport's report
# ---------------------------------------------------------------------------
def _grade_fg_line(fg_actual_total, prob, fg_line):
    """
    Grade a single full-game over/under probability call.
    If the model says prob > 0.50 it calls OVER, else UNDER.
    Returns: ('WIN'|'LOSS'|'PUSH'|'PENDING', 'OVER'|'UNDER'|'PENDING')
    """
    if prob is None:
        return 'PENDING', 'N/A'
    model_call = 'OVER' if prob >= 0.50 else 'UNDER'
    if fg_actual_total is None:
        return 'PENDING', model_call
    if fg_actual_total > fg_line:
        actual = 'OVER'
    elif fg_actual_total < fg_line:
        actual = 'UNDER'
    else:
        actual = 'PUSH'

    if actual == 'PUSH':
        return 'PUSH', model_call
    return ('WIN' if model_call == actual else 'LOSS'), model_call


def grade_report(sport_id, line, schedule_date, filepath_override=None, grade_fg=True, grading_mode='fixed'):
    label = SPORT_LABELS.get(sport_id, f'Sport {sport_id}')
    filepath = filepath_override if filepath_override else get_report_filepath(sport_id, schedule_date)

    if not filepath or not os.path.exists(filepath):
        print(f"\n[{label}] No report found at {filepath}")
        return

    print(f"\n{'='*60}")
    if grading_mode == 'all':
        title = f"PORTFOLIO GRADER (ALL GAMES - Line: {line})"
    else:
        title = f"PORTFOLIO GRADER (GATEKEEPER ONLY - Line: {line})"
        
    print(f"  {label} {title}")
    print(f"{'='*60}")
    print(f"  Report: {os.path.basename(filepath)}")
    print(f"  Date:   {schedule_date}")

    # Fetch today's schedule for this sport to map games to IDs
    schedule = None
    for attempt in range(3):
        try:
            schedule = statsapi.schedule(sportId=sport_id, date=schedule_date)
            break
        except Exception:
            if attempt < 2:
                time.sleep(3)
            else:
                print(f"  Failed to fetch schedule after 3 attempts.")
                return

    games = parse_report(filepath, line=line, grading_mode=grading_mode)

    if not games:
        print(f"  No Action Matrix projections parsed from report.")
        return

    # F5 counters
    wins = 0
    losses = 0
    skips = 0
    pending = 0
    
    skipped_list = []

    # Full Game counters per line
    fg_results = {
        7.5: {'wins': 0, 'losses': 0, 'pushes': 0, 'pending': 0},
        8.5: {'wins': 0, 'losses': 0, 'pushes': 0, 'pending': 0},
        9.5: {'wins': 0, 'losses': 0, 'pushes': 0, 'pending': 0},
    }
    fg_prob_keys = {7.5: 'fg_over_7_5', 8.5: 'fg_over_8_5', 9.5: 'fg_over_9_5'}

    for g in games:
        gid = find_game_id(g['matchup'], schedule)

        actual_total = None
        fg_actual_total = None
        if gid:
            try:
                box = statsapi.get('game', {'gamePk': gid, 'hydrate': 'linescore'})
                innings = box.get('liveData', {}).get('linescore', {}).get('innings', [])
                if len(innings) >= 5:
                    a_runs = sum(inn.get('away', {}).get('runs', 0) for inn in innings[:5])
                    h_runs = sum(inn.get('home', {}).get('runs', 0) for inn in innings[:5])
                    actual_total = a_runs + h_runs
                if innings:
                    a_runs_fg = sum(inn.get('away', {}).get('runs', 0) for inn in innings)
                    h_runs_fg = sum(inn.get('home', {}).get('runs', 0) for inn in innings)
                    fg_actual_total = a_runs_fg + h_runs_fg
            except:
                pass

        # --- Action Matrix Grading ---
        if g['action_bet'] == "SKIP":
            verdict = "[SKIP] "
            skips += 1
            actual_str = f"{actual_total} runs (F5)" if actual_total is not None else "N/A"
            skipped_list.append(f"{g['matchup']} (Line: {g['game_line']})")
        elif g['action_bet'] in ("OVER", "UNDER"):
            if actual_total is None:
                actual_result = "N/A"
                verdict = "[PENDING]"
                pending += 1
            else:
                if actual_total < g['game_line']:
                    actual_result = "UNDER"
                elif actual_total > g['game_line']:
                    actual_result = "OVER"
                else:
                    actual_result = "PUSH"

                if actual_result == "PUSH":
                    verdict = "[PUSH] "
                    skips += 1
                elif g['action_bet'] == actual_result:
                    verdict = "[WIN]  "
                    wins += 1
                else:
                    verdict = "[LOSS] "
                    losses += 1
            actual_str = f"{actual_total} runs (F5 {actual_result})" if actual_total is not None else "N/A"

        elif g['action_bet'] == "FG_OVER":
            fg_line_target = g.get('fg_line_for_over')
            if fg_actual_total is None or fg_line_target is None:
                actual_result = "N/A"
                verdict = "[PENDING]"
                pending += 1
            else:
                if fg_actual_total > fg_line_target:
                    actual_result = "OVER"
                elif fg_actual_total < fg_line_target:
                    actual_result = "UNDER"
                else:
                    actual_result = "PUSH"

                if actual_result == "PUSH":
                    verdict = "[PUSH] "
                    skips += 1
                elif actual_result == "OVER":
                    verdict = "[WIN]  "
                    wins += 1
                else:
                    verdict = "[LOSS] "
                    losses += 1
            actual_str = f"{fg_actual_total} runs (FG {actual_result} vs {fg_line_target})" if fg_actual_total is not None else "N/A"

        fg_str = f"  [Full Game: {fg_actual_total} runs]" if fg_actual_total is not None else ""

        print(f"\n  {g['matchup']} (Line: {g['game_line']})")
        print(f"    Action  : {g['action_raw']}")
        print(f"    Result  : {actual_str}  |  {verdict}{fg_str}")

        # --- Full Game grading ---
        if grade_fg:
            fg_line_labels = []
            for fg_line in [7.5, 8.5, 9.5]:
                prob = g.get(fg_prob_keys[fg_line])
                result, model_call = _grade_fg_line(fg_actual_total, prob, fg_line)

                if result == 'PENDING':
                    fg_results[fg_line]['pending'] += 1
                elif result == 'WIN':
                    fg_results[fg_line]['wins'] += 1
                elif result == 'LOSS':
                    fg_results[fg_line]['losses'] += 1
                elif result == 'PUSH':
                    fg_results[fg_line]['pushes'] += 1

                prob_str = f"{int(prob*100)}%" if prob is not None else "N/A"
                fg_line_labels.append(f"O{fg_line} {model_call}({prob_str}) [{result}]")

            print(f"    FG Probs: {' | '.join(fg_line_labels)}")

    # --- Action Matrix Summary ---
    graded = wins + losses
    win_pct = (wins / graded * 100) if graded > 0 else 0
    print(f"\n  {'-'*56}")
    print(f"  Matrix Summary -> Wins: {wins} | Losses: {losses} | Pushes/Skips: {skips} | Pending: {pending}")
    print(f"  Matrix Win Rate -> {win_pct:.1f}% ({wins}/{graded} graded)")

    if skipped_list:
        print(f"\n  Skipped Games ({len(skipped_list)}):")
        for sg in skipped_list:
            print(f"    - {sg}")

    # --- Full Game Summary ---
    if grade_fg:
        print(f"\n  {'-'*56}")
        print(f"  FULL GAME PROBS Summary")
        for fg_line in [7.5, 8.5, 9.5]:
            r = fg_results[fg_line]
            fg_graded = r['wins'] + r['losses']
            fg_pct = (r['wins'] / fg_graded * 100) if fg_graded > 0 else 0
            print(f"    Over {fg_line}: {fg_pct:.1f}% ({r['wins']}W/{r['losses']}L | "
                  f"Pushes: {r['pushes']} | Pending: {r['pending']})")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grade markdown reports based on Top-Down F5 projection AND Full Game Probs')
    parser.add_argument('--sportId', type=int, default=1, help='Grade a specific sport (1=MLB, 11=AAA, 12=AA)')
    parser.add_argument('--line', type=float, default=4.5, help='The F5 line to grade against (default 4.5)')
    parser.add_argument('--no-fg', action='store_true', help='Skip Full Game Probs grading')
    parser.add_argument('--all', action='store_true', help='Grade all games, forcing a pick on skipped games using the Top-Down projection')

    parser.add_argument('--date', type=str, default=None, help='Date for API lookup (default: auto-detected from file or today KST)')
    parser.add_argument('--file', type=str, default=None, help='Specific markdown report file to grade')

    args = parser.parse_args()

    # Auto-detect date from file if not explicitly provided
    resolved_date = args.date
    if not resolved_date and args.file and os.path.exists(args.file):
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Look for "**Date:** 06/30/2026"
                date_match = re.search(r'\*\*Date:\*\*\s*(\d{2}/\d{2}/\d{4})', content)
                if date_match:
                    resolved_date = date_match.group(1)
        except Exception:
            pass
            
    # Fallback to today KST
    if not resolved_date:
        dt_kst = datetime.now(timezone(timedelta(hours=9)))
        resolved_date = dt_kst.strftime('%m/%d/%Y')

    grading_mode = 'fixed'
    if args.all:
        grading_mode = 'all'

    grade_report(args.sportId, args.line, resolved_date, filepath_override=args.file, grade_fg=not args.no_fg, grading_mode=grading_mode)
