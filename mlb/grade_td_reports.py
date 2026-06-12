"""
grade_td_reports.py
===================
Grades the existing markdown reports, but PURELY based on the
"Top-Down Projected F5 Total" against a specific line (e.g., 4.5).
It does not re-run the model, making it incredibly fast.

Usage:
    python mlb/grade_td_reports.py                          # grades MLB against 4.5
    python mlb/grade_td_reports.py --sportId 11             # grades AAA against 4.5
    python mlb/grade_td_reports.py --line 5.5               # grades against 5.5
"""
import time
import os, re, sys, argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import statsapi

# ---------------------------------------------------------------------------
# Report file map
# ---------------------------------------------------------------------------
REPORT_FILES = {
    1:  os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consensus_f5_v3_report.md'),
    11: os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consensus_f5_v3_report_AAA.md'),
    12: os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consensus_f5_v3_report_AA.md'),
}

SPORT_LABELS = {1: 'MLB', 11: 'AAA', 12: 'AA'}


# ---------------------------------------------------------------------------
# Report parser
# ---------------------------------------------------------------------------
def parse_report(filepath, line=4.5):
    """
    Parses a markdown report and extracts the Top-Down projection.
    Returns a list of dicts:
        matchup  : "Away Team @ Home Team"
        td_total : float
        td_bet   : "OVER" / "UNDER" / "PUSH"
    """
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    games = []
    blocks = re.split(r'\n(?=###\s)', content.strip())

    for block in blocks:
        if not block.startswith('###'):
            continue

        # --- Matchup name ---
        header_match = re.match(r'###\s+(?:🚨\s*)?(.*)', block)
        if not header_match:
            continue
        raw_header = header_match.group(1).strip()
        matchup = re.sub(r'\s*\([^)]*\)', '', raw_header).strip()

        # --- Parse Top-Down Projected F5 Total ---
        td_match = re.search(r'-\s*\*\*Top-Down Projected F5 Total:\*\*\s*(\d+\.?\d*)', block)
        if not td_match:
            continue
            
        td_total = float(td_match.group(1))
        
        # Determine bet against the line
        if td_total < line:
            td_bet = "UNDER"
        elif td_total > line:
            td_bet = "OVER"
        else:
            td_bet = "PUSH"

        games.append({
            'matchup': matchup, 
            'td_total': td_total,
            'td_bet': td_bet
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
def grade_report(sport_id, line, schedule_date, filepath_override=None):
    label = SPORT_LABELS.get(sport_id, f'Sport {sport_id}')
    filepath = filepath_override if filepath_override else REPORT_FILES.get(sport_id)

    if not filepath or not os.path.exists(filepath):
        print(f"\n[{label}] No report found at {filepath}")
        return

    print(f"\n{'='*60}")
    print(f"  {label} TOP-DOWN GRADER (Line: {line})")
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

    games = parse_report(filepath, line=line)

    if not games:
        print(f"  No Top-Down projections parsed from report.")
        return

    wins = 0
    losses = 0
    skips = 0
    pending = 0

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
        
        if actual_total is None:
            actual_result = "N/A"
            verdict = "[PENDING]"
            pending += 1
        else:
            if actual_total < line:
                actual_result = "UNDER"
            elif actual_total > line:
                actual_result = "OVER"
            else:
                actual_result = "PUSH"
                
            if g['td_bet'] == "PUSH" or actual_result == "PUSH":
                verdict = "[PUSH] "
                skips += 1
            elif g['td_bet'] == actual_result:
                verdict = "[WIN]  "
                wins += 1
            else:
                verdict = "[LOSS] "
                losses += 1
                
        actual_str = f"{actual_total} runs ({actual_result})" if actual_total is not None else "N/A"
        if g['td_bet'] == "OVER" and fg_actual_total is not None:
            actual_str += f"  [Full Game: {fg_actual_total} runs]"
        
        print(f"\n  {g['matchup']}")
        print(f"    TD Proj: {g['td_total']:.2f} -> Bet {g['td_bet']} {line}")
        print(f"    Actual : {actual_str}  |  {verdict}")

    graded = wins + losses
    win_pct = (wins / graded * 100) if graded > 0 else 0
    print(f"\n  ------------------------------------")
    print(f"  Summary -> Wins: {wins} | Losses: {losses} | Pushes/Skips: {skips} | Pending: {pending}")
    print(f"  Win Rate -> {win_pct:.1f}% ({wins}/{graded} graded picks)\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grade markdown reports based strictly on Top-Down projection vs a specific line')
    parser.add_argument('--sportId', type=int, default=1, help='Grade a specific sport (1=MLB, 11=AAA, 12=AA)')
    parser.add_argument('--line', type=float, default=4.5, help='The F5 line to grade against (default 4.5)')
    
    # KST date for default (matching typical daily flow)
    dt_kst = datetime.now(timezone(timedelta(hours=9)))
    default_date = dt_kst.strftime('%m/%d/%Y')
    parser.add_argument('--date', type=str, default=default_date, help='Date for API lookup (default: today KST)')
    parser.add_argument('--file', type=str, default=None, help='Specific markdown report file to grade')
    
    args = parser.parse_args()
    
    grade_report(args.sportId, args.line, args.date, filepath_override=args.file)
