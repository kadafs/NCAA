"""
grade_reports.py
================
Grades the existing consensus report markdown files against actual game results.
No re-running of the model. Just reads the picks from the reports and checks scores.

Usage:
    python mlb/grade_reports.py                          # grades all 3 reports (MLB, AAA, AA)
    python mlb/grade_reports.py --sportId 1              # MLB only
    python mlb/grade_reports.py --line 4.5               # grade against a specific line
    python mlb/grade_reports.py --line 4.5 --line 5.5   # grade multiple lines
"""
import time

import os, re, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import statsapi

# ---------------------------------------------------------------------------
# Report file map
# ---------------------------------------------------------------------------
REPORT_FILES = {
    1:  os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consensus_f5_report.md'),
    11: os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consensus_f5_report_AAA.md'),
    12: os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consensus_f5_report_AA.md'),
}

SPORT_LABELS = {1: 'MLB', 11: 'AAA', 12: 'AA'}


# ---------------------------------------------------------------------------
# Report parser
# ---------------------------------------------------------------------------
def parse_report(filepath, target_lines=None):
    """
    Parses a consensus markdown report and returns a list of game dicts.

    Each dict:
        matchup   : "Away Team @ Home Team"
        picks     : {4.5: 'OVER'/'UNDER'/'Skip', ...}  for each line
    """
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    games = []
    # Split by game block (each starts with "### ")
    blocks = re.split(r'\n(?=###\s)', content.strip())

    for block in blocks:
        if not block.startswith('###'):
            continue

        # --- Matchup name (strip pitcher names in parens) ---
        header_match = re.match(r'###\s+(.*)', block)
        if not header_match:
            continue
        raw_header = header_match.group(1).strip()
        # Remove pitcher names: "Team (Pitcher) @ Team (Pitcher)" -> "Team @ Team"
        matchup = re.sub(r'\s*\([^)]*\)', '', raw_header).strip()

        # --- Parse action matrix lines ---
        # e.g. "  - If Line is **4.5** -> Bet **OVER** | MC Under Probability: 21%"
        #   or "  - If Line is **3.5** -> Skip | MC Under Probability: 50%"
        picks = {}
        line_pattern = re.compile(
            r'If Line is \*\*(\d+\.?\d*)\*\*\s*->\s*(?:Bet \*\*(\w+)\*\*|(\w+))',
            re.IGNORECASE
        )
        for m in line_pattern.finditer(block):
            line_val = float(m.group(1))
            bet = m.group(2) or m.group(3)   # group(2) = bolded bet, group(3) = plain Skip
            if target_lines and line_val not in target_lines:
                continue
            picks[line_val] = bet.capitalize()  # 'Over', 'Under', 'Skip'

        if matchup and picks:
            games.append({'matchup': matchup, 'picks': picks})

    return games


# ---------------------------------------------------------------------------
# Fetch actual F5 score from statsapi
# ---------------------------------------------------------------------------
def get_actual_f5(game_id, retries=3):
    """Returns (away_runs, home_runs) for the first 5 innings, or None."""
    for attempt in range(retries):
        try:
            data = statsapi.get('game', {'gamePk': game_id, 'hydrate': 'linescore'})
            innings = data.get('liveData', {}).get('linescore', {}).get('innings', [])
            if len(innings) < 5:
                return None
            away = sum(inn.get('away', {}).get('runs', 0) for inn in innings[:5])
            home = sum(inn.get('home', {}).get('runs', 0) for inn in innings[:5])
            return away, home
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return None


# ---------------------------------------------------------------------------
# Match a parsed matchup name to a scheduled game
# ---------------------------------------------------------------------------
def find_game_id(matchup, schedule):
    """
    Fuzzy-match 'Away @ Home' to a game in the schedule list.
    Handles name mismatches (e.g. 'Athletics' vs 'Oakland Athletics').
    """
    if ' @ ' not in matchup:
        return None
    away_q, home_q = [t.strip().lower() for t in matchup.split(' @ ', 1)]

    for g in schedule:
        away_s = g['away_name'].lower()
        home_s = g['home_name'].lower()
        # Substring match (handles 'athletics' matching 'oakland athletics')
        if away_q in away_s or away_s in away_q:
            if home_q in home_s or home_s in home_q:
                return g['game_id']
    return None


# ---------------------------------------------------------------------------
# Grade a single sport's report
# ---------------------------------------------------------------------------
def grade_report(sport_id, target_lines, schedule_date):
    label = SPORT_LABELS.get(sport_id, f'Sport {sport_id}')
    filepath = REPORT_FILES.get(sport_id)
    if not filepath or not os.path.exists(filepath):
        print(f"\n[{label}] Report not found: {filepath}")
        return

    # Extract date from report header
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', first_line)
    report_date = date_match.group(1) if date_match else None

    # Use schedule_date arg if provided, else fall back to report date
    fetch_date = schedule_date or report_date
    if not fetch_date:
        print(f"\n[{label}] Could not determine date from report header.")
        return

    # Convert YYYY-MM-DD to MM/DD/YYYY for statsapi
    if '-' in fetch_date:
        parts = fetch_date.split('-')
        fetch_date_api = f"{parts[1]}/{parts[2]}/{parts[0]}"
    else:
        fetch_date_api = fetch_date  # already MM/DD/YYYY

    print(f"\n{'='*62}")
    print(f"  {label} GRADE REPORT  |  {report_date or fetch_date}")
    print(f"{'='*62}")

    for attempt in range(3):
        try:
            schedule = statsapi.schedule(sportId=sport_id, date=fetch_date_api)
            break
        except Exception:
            if attempt < 2:
                print(f"  API timeout, retrying ({attempt+1}/3)...")
                time.sleep(3)
            else:
                print(f"  [{label}] Failed to fetch schedule after 3 attempts. Skipping.")
                return
    games = parse_report(filepath, target_lines=target_lines)

    if not games:
        print(f"  No picks parsed from report.")
        return

    # Grade per line
    line_stats = {ln: {'wins': 0, 'losses': 0, 'skips': 0, 'pending': 0} for ln in target_lines}

    rows = []
    for g in games:
        gid = find_game_id(g['matchup'], schedule)
        actual = get_actual_f5(gid) if gid else None
        actual_total = (actual[0] + actual[1]) if actual else None

        row = {
            'matchup': g['matchup'],
            'picks': g['picks'],
            'actual': actual_total,
            'gid': gid,
        }
        rows.append(row)

        for ln in target_lines:
            pick = g['picks'].get(ln, 'Skip')
            if pick == 'Skip':
                line_stats[ln]['skips'] += 1
                continue
            if actual_total is None:
                line_stats[ln]['pending'] += 1
                continue
            actual_side = 'Over' if actual_total > ln else 'Under'
            if pick == actual_side:
                line_stats[ln]['wins'] += 1
            else:
                line_stats[ln]['losses'] += 1

    # Print game-by-game breakdown
    for row in rows:
        actual_str = f"{row['actual']} runs" if row['actual'] is not None else 'Pending'
        print(f"\n  {row['matchup']}")
        print(f"  Actual F5: {actual_str}")

        for ln in target_lines:
            pick = row['picks'].get(ln, 'Skip')
            if pick == 'Skip':
                verdict = 'SKIP'
            elif row['actual'] is None:
                verdict = 'PENDING'
            else:
                actual_side = 'Over' if row['actual'] > ln else 'Under'
                verdict = 'WIN  +' if pick == actual_side else 'LOSS X'
            print(f"    Line {ln:>4}: {pick:<6} -> {verdict}")

    # Print summary per line
    print(f"\n{'='*62}")
    print(f"  SUMMARY")
    print(f"{'='*62}")
    print(f"  {'LINE':<8}  {'W':>4}  {'L':>4}  {'SKIP':>5}  {'WIN%':>7}")
    print(f"  {'-'*40}")
    for ln in target_lines:
        s = line_stats[ln]
        graded = s['wins'] + s['losses']
        pct = f"{s['wins']/graded*100:.1f}%" if graded > 0 else "N/A"
        print(f"  {ln:<8}  {s['wins']:>4}  {s['losses']:>4}  {s['skips']:>5}  {pct:>7}")
    print(f"{'='*62}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grade consensus report picks against actual results')
    parser.add_argument('--sportId', type=int, nargs='+', default=[1, 11, 12],
                        help='Sport IDs to grade (1=MLB, 11=AAA, 12=AA). Default: all three.')
    parser.add_argument('--line', type=float, nargs='+', default=[4.5],
                        help='Line(s) to grade against. Default: 4.5')
    parser.add_argument('--date', type=str, default=None,
                        help='Override date in MM/DD/YYYY or YYYY-MM-DD format.')
    args = parser.parse_args()

    for sid in args.sportId:
        grade_report(sid, sorted(args.line), args.date)
