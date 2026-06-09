"""
grade_intl_reports.py
===================
Grades the existing markdown reports for KBO and NPB based on the
"Top-Down Projected F5 Total" against a specific line (e.g., 4.5).

Since KBO and NPB lack a unified, easily accessible API for historical
linescores, this script grades against manual actuals stored in:
`actuals/kbo_actuals_YYYYMMDD.json` or `actuals/npb_actuals_YYYYMMDD.json`.

Usage:
    python grade_intl_reports.py --league KBO                 
    python grade_intl_reports.py --league NPB --line 5.5               
"""
import os, re, argparse, json
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Report parser
# ---------------------------------------------------------------------------
def parse_report(filepath, line=4.5):
    """
    Parses an international markdown report and extracts the Top-Down projection.
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
# Grade a single league's report
# ---------------------------------------------------------------------------
def grade_report(league, line, schedule_date):
    league = league.lower()
    
    # Path to the report (e.g., kbo/kbo_f5_report_06-08-2026.md)
    safe_date = schedule_date.replace('/', '-')
    filepath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        league, 
        f'{league}_f5_report_{safe_date}.md'
    )

    if not os.path.exists(filepath):
        print(f"\n[{league.upper()}] No report found at {filepath}")
        return

    print(f"\n{'='*60}")
    print(f"  {league.upper()} TOP-DOWN GRADER (Line: {line})")
    print(f"{'='*60}")
    print(f"  Report: {os.path.basename(filepath)}")
    print(f"  Date:   {schedule_date}")

    games = parse_report(filepath, line=line)

    if not games:
        print(f"  No Top-Down projections parsed from report.")
        return

    # Load actuals if they exist
    actuals_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        'actuals', 
        f'{league}_actuals_{safe_date}.json'
    )
    
    actuals_map = {}
    if os.path.exists(actuals_path):
        try:
            with open(actuals_path, 'r', encoding='utf-8') as f:
                actuals_map = json.load(f)
        except Exception as e:
            print(f"  Warning: Could not parse actuals file: {e}")
    else:
        print(f"  (No actuals file found at {actuals_path}. All games will be PENDING.)")

    wins = 0
    losses = 0
    skips = 0
    pending = 0

    for g in games:
        matchup = g['matchup']
        
        # Try to find the actual F5 score for this matchup in the actuals_map
        actual_total = None
        
        # Fuzzy matching against actuals map
        for key, val in actuals_map.items():
            if key.lower() in matchup.lower() or matchup.lower() in key.lower():
                actual_total = val
                break
        
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
        
        print(f"\n  {g['matchup']}")
        print(f"    TD Proj: {g['td_total']:.2f} -> Bet {g['td_bet']} {line}")
        print(f"    Actual : {actual_str}  |  {verdict}")

    graded = wins + losses
    win_pct = (wins / graded * 100) if graded > 0 else 0
    print(f"\n  ------------------------------------")
    print(f"  Summary -> Wins: {wins} | Losses: {losses} | Pushes/Skips: {skips} | Pending: {pending}")
    print(f"  Win Rate -> {win_pct:.1f}% ({wins}/{graded} graded picks)\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grade international markdown reports based strictly on Top-Down projection vs a specific line')
    parser.add_argument('--league', type=str, required=True, choices=['KBO', 'NPB'], help='Grade KBO or NPB')
    parser.add_argument('--line', type=float, default=4.5, help='The F5 line to grade against (default 4.5)')
    
    # KST/JST date for default
    dt_kst = datetime.now(timezone(timedelta(hours=9)))
    default_date = dt_kst.strftime('%m/%d/%Y')
    parser.add_argument('--date', type=str, default=default_date, help='Date of the report (default: today KST/JST)')
    
    args = parser.parse_args()
    
    grade_report(args.league, args.line, args.date)
