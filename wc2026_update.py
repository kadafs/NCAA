"""
wc2026_update.py
================
Daily results updater for run_wc2026.py.

Paste today's completed scores and this script inserts them into
ACTUAL_RESULTS in run_wc2026.py — no manual file editing required.

Usage:
    python wc2026_update.py                          # interactive mode
    python wc2026_update.py --result "Spain 2-0 Cabo Verde"
    python wc2026_update.py --result "Belgium 1-0 Egypt" --result "Saudi Arabia 0-1 Uruguay"
    python wc2026_update.py --check                  # show what results are already in
    python wc2026_update.py --today                  # show today's fixtures (upcoming)
"""

import sys
import os
import re
import ast
import argparse
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "run_wc2026.py")

# Team name normalisation — maps common shorthand to exact fixture names
NAME_MAP = {
    "ivory coast": "Côte d'Ivoire", "cote d ivoire": "Côte d'Ivoire",
    "curacao": "Curaçao", "cape verde": "Cabo Verde",
    "iran": "IR Iran", "dr congo": "Congo DR", "drc": "Congo DR",
    "south korea": "Korea Republic", "korea": "Korea Republic",
    "czechia": "Czechia", "czech republic": "Czechia",
    "turkey": "Türkiye", "usa": "USA", "united states": "USA",
    "bosnia": "Bosnia and Herzegovina",
    "nz": "New Zealand", "new zealand": "New Zealand",
    "uruguay": "Uruguay", "saudi": "Saudi Arabia",
}

def normalise(name: str) -> str:
    n = name.strip()
    low = n.lower()
    return NAME_MAP.get(low, n)

def parse_result(text: str):
    """Parse 'Team A N-M Team B' → (home, hg, ag, away)."""
    m = re.match(
        r"^(.+?)\s+(\d+)\s*[-–:]\s*(\d+)\s+(.+)$",
        text.strip(), re.IGNORECASE
    )
    if not m:
        return None
    home = normalise(m.group(1).strip())
    hg   = int(m.group(2))
    ag   = int(m.group(3))
    away = normalise(m.group(4).strip())
    return home, hg, ag, away

def load_script() -> str:
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

def save_script(content: str):
    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(content)

def get_existing_results(content: str) -> dict:
    """Extract all un-commented result tuples from ACTUAL_RESULTS block."""
    in_block = False
    results  = {}
    for line in content.splitlines():
        if "ACTUAL_RESULTS" in line and "=" in line:
            in_block = True
        if in_block:
            if line.strip().startswith("#"):
                continue
            m = re.search(r'\("([^"]+)"\s*,\s*"([^"]+)"\)\s*:\s*\((\d+)\s*,\s*(\d+)\)', line)
            if m:
                results[(m.group(1), m.group(2))] = (int(m.group(3)), int(m.group(4)))
            if in_block and line.strip() == "}":
                break
    return results

def insert_result(content: str, home: str, hg: int, ag: int, away: str) -> str:
    """Insert a result line before the closing } of ACTUAL_RESULTS."""
    today_str = datetime.now(timezone.utc).strftime("%b %d")
    new_line  = f'    ("{home}",\t"{away}"):\t\t({hg}, {ag}),   # {today_str} ✓'
    # Find the closing MATCHDAY 3 comment block or the closing }
    insert_marker = "# ─── MATCHDAY 3 RESULTS"
    if insert_marker in content:
        return content.replace(
            insert_marker,
            new_line + "\n\n    " + insert_marker,
            1
        )
    # Fallback: insert before the closing brace
    lines = content.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == "}" and i > 0:
            if "ACTUAL_RESULTS" in "\n".join(lines[max(0, i-40):i]):
                lines.insert(i, new_line)
                return "\n".join(lines)
    return content

def show_today_fixtures():
    """Import and display today's upcoming fixtures."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_wc2026", SCRIPT_PATH)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print(f"\n  📅 Fixtures on {today}:")
        print(f"  {'─'*60}")
        found = False
        for (h, a, dt, venue, grp, md) in mod.WC2026_FIXTURES:
            if dt == today:
                done = (h, a) in mod.ACTUAL_RESULTS
                status = "✅ Result logged" if done else "🔮 Upcoming"
                print(f"  Group {grp} MD{md}  {h} vs {a}")
                print(f"            {venue}  {status}")
                found = True
        if not found:
            print("  No fixtures found for today.")
        print()
    except Exception as e:
        print(f"  Error: {e}")

def show_existing(content: str):
    results = get_existing_results(content)
    print(f"\n  ✅ Results currently in ACTUAL_RESULTS ({len(results)} games):")
    print(f"  {'─'*56}")
    for (h, a), (hg, ag) in results.items():
        print(f"  {h} {hg}-{ag} {a}")
    print()

def interactive_mode(content: str) -> str:
    print("\n  ⚽ WC2026 Result Updater — Interactive Mode")
    print("  Enter results in format:  Team A N-M Team B")
    print("  Type 'done' when finished.\n")
    while True:
        raw = input("  Result> ").strip()
        if raw.lower() in ("done", "exit", "quit", ""):
            break
        parsed = parse_result(raw)
        if not parsed:
            print("  ❌ Could not parse. Use format: 'Spain 2-0 Cabo Verde'")
            continue
        home, hg, ag, away = parsed
        existing = get_existing_results(content)
        if (home, away) in existing:
            print(f"  ⚠️  Already have: {home} {existing[(home,away)][0]}-{existing[(home,away)][1]} {away}")
            cont = input("     Overwrite? (y/N): ").strip().lower()
            if cont != "y":
                continue
        content = insert_result(content, home, hg, ag, away)
        print(f"  ✅ Added: {home} {hg}-{ag} {away}")
    return content

def main():
    ap = argparse.ArgumentParser(description="WC2026 Daily Results Updater")
    ap.add_argument("--result", "-r", action="append",
                    help="Result string, e.g. 'Spain 2-0 Cabo Verde'")
    ap.add_argument("--check",  action="store_true", help="Show all logged results")
    ap.add_argument("--today",  action="store_true", help="Show today's fixtures")
    args = ap.parse_args()

    content = load_script()

    if args.today:
        show_today_fixtures()
        return

    if args.check:
        show_existing(content)
        return

    if args.result:
        for raw in args.result:
            parsed = parse_result(raw)
            if not parsed:
                print(f"  ❌ Cannot parse: '{raw}'  — use 'Team A N-M Team B'")
                continue
            home, hg, ag, away = parsed
            existing = get_existing_results(content)
            if (home, away) in existing:
                print(f"  ⚠️  Already logged: {home} {existing[(home,away)][0]}-{existing[(home,away)][1]} {away}  (skipping)")
                continue
            content = insert_result(content, home, hg, ag, away)
            print(f"  ✅ {home} {hg}-{ag} {away}")
        save_script(content)
        print(f"\n  💾 Saved to run_wc2026.py")
        print(f"  Run: python run_wc2026.py --completed --standings to review.\n")
        return

    # No flags → interactive
    updated = interactive_mode(content)
    save_script(updated)
    print(f"\n  💾 Saved. Run: python run_wc2026.py --upcoming --standings\n")

if __name__ == "__main__":
    main()
