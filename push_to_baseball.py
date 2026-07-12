#!/usr/bin/env python3
"""
push_to_baseball.py
────────────────────
Data Bridge: copies freshly generated prediction files from ncaa-api/data/baseball
into the baseball-dashboard repository, then commits and pushes to GitHub.

Usage:
    python push_to_baseball.py
    
    # With a specific date override:
    python push_to_baseball.py --date 2026-03-30
"""

import os
import sys
import shutil
import subprocess
import argparse
import re
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ── Configuration ──────────────────────────────────────────────────────────────
NCAA_API_ROOT   = Path(__file__).parent
DASHBOARD_ROOT  = NCAA_API_ROOT.parent / "baseball-dashboard"

# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: Path):
    """Run a shell command and print output. Raises on failure."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        print(f"  ❌ Error: {result.stderr.strip()}", file=sys.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout.strip()

def copy_baseball_data(date_filter: str | None = None):
    """
    Copy prediction files for baseball from ncaa-api/data/baseball
    into baseball-dashboard/public/data/baseball.

    Handles both league-prefixed files (new):
        universal_predictions_MLB_2026-07-12.json
        universal_predictions_AAA_2026-07-12.json
    And legacy date-only files (old):
        universal_predictions_2026-07-12-confirmed.json  →  universal_predictions_2026-07-12.json

    If date_filter is provided (YYYY-MM-DD), only copies files for that date.
    Otherwise copies up to 14 recent days.
    """
    src_dir  = NCAA_API_ROOT / "data" / "baseball"
    dest_dir = DASHBOARD_ROOT / "public" / "data" / "baseball"

    if not src_dir.exists():
        print(f"  ⚠️ Source directory not found: {src_dir}")
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)

    all_files = list(src_dir.glob("universal_predictions_*.json"))
    if not all_files:
        print(f"  ⚠️ No prediction files found in {src_dir}")
        return []

    # Match new league-prefixed format: universal_predictions_{LEAGUE}_{DATE}.json
    LEAGUE_PREFIX_RE = re.compile(r"universal_predictions_([A-Za-z0-9\-]+)_(\d{4}-\d{2}-\d{2})\.json")
    # Match legacy format: universal_predictions_{DATE}-{suffix}.json
    LEGACY_RE        = re.compile(r"universal_predictions_(\d{4}-\d{2}-\d{2})-?\w*\.json")

    # Build a map of dest_filename → source Path
    dest_to_src: dict[str, Path] = {}
    dates_seen: set[str] = set()

    for f in all_files:
        m_league = LEAGUE_PREFIX_RE.match(f.name)
        m_legacy = LEGACY_RE.match(f.name)

        if m_league:
            league, date_str = m_league.group(1), m_league.group(2)
            dest_name = f"universal_predictions_{league}_{date_str}.json"
        elif m_legacy:
            date_str = m_legacy.group(1)
            dest_name = f"universal_predictions_{date_str}.json"   # legacy fallback
        else:
            continue

        dates_seen.add(date_str)
        # Keep most recently modified if duplicates exist
        if dest_name not in dest_to_src or f.stat().st_mtime > dest_to_src[dest_name].stat().st_mtime:
            dest_to_src[dest_name] = f

    # Apply date filter or limit to 14 most recent dates
    sorted_dates = sorted(dates_seen, reverse=True)
    if date_filter:
        allowed_dates = {date_filter}
    else:
        allowed_dates = set(sorted_dates[:14])

    copied = []
    for dest_name, src_path in sorted(dest_to_src.items()):
        # Extract date from dest_name to check allowed_dates
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", dest_name)
        if not date_match or date_match.group(1) not in allowed_dates:
            continue

        dest_file = dest_dir / dest_name
        print(f"  📄 Copying: {src_path.name} → {dest_name}")
        shutil.copy2(src_path, dest_file)
        copied.append(dest_name)

    print(f"  ✅ Copied {len(copied)} file(s) for baseball.")
    return copied

def cleanup_old_files(keep_days: int = 14):
    """
    Remove universal_predictions_*.json files older than keep_days
    from the dashboard repo to prevent git history from ballooning.
    Handles both league-prefixed and legacy filenames.
    """
    from datetime import timedelta
    dest_dir = DASHBOARD_ROOT / "public" / "data" / "baseball"
    if not dest_dir.exists():
        return

    cutoff = date.today() - timedelta(days=keep_days)
    removed = []
    for f in dest_dir.glob("universal_predictions_*.json"):
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if not date_match:
            continue
        try:
            file_date = date.fromisoformat(date_match.group(1))
            if file_date < cutoff:
                f.unlink()
                removed.append(f.name)
        except ValueError:
            pass

    if removed:
        print(f"  🗑️  Cleaned up {len(removed)} old baseball file(s): {', '.join(removed)}")
    else:
        print(f"  ✅ No old baseball files to clean up (keeping last {keep_days} days).")

def git_commit_and_push(copied_files: list[str], dashboard_root: Path):
    """Stage changed files, create a commit, and push to GitHub."""

    # Check if it's a git repo
    git_dir = dashboard_root / ".git"
    if not git_dir.exists():
        print("\n  ⚠️  baseball-dashboard is not a Git repository yet.")
        print("  Run:  cd \"../baseball-dashboard\" && git init && git remote add origin <YOUR_REPO_URL>")
        print("  Then re-run this script.")
        return

    # Run sync-data.js to regenerate dates_index.json
    sync_script = dashboard_root / "scripts" / "sync-data.js"
    if sync_script.exists():
        print("  🔄 Rebuilding dates_index.json...")
        run(["node", "scripts/sync-data.js"], cwd=dashboard_root)

    # Stage all changes in public/data
    run(["git", "add", "public/data/"], cwd=dashboard_root)

    if not copied_files:
        print("  ℹ️  Nothing new to commit.")
        return

    today = date.today().isoformat()
    commit_msg = f"data: push predictions {today} — baseball: {', '.join(copied_files)}"

    # Check if there's anything staged
    status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=dashboard_root
    )
    if status.returncode == 0:
        print("  ℹ️  No staged changes to commit. Data may already be up to date.")
        return

    run(["git", "commit", "-m", commit_msg], cwd=dashboard_root)
    print(f"\n  🚀 Pushing to GitHub...")
    try:
        run(["git", "push"], cwd=dashboard_root)
    except RuntimeError:
        print("  ⚠️ Standard push failed (likely no upstream branch). Attempting to set upstream...")
        run(["git", "push", "-u", "origin", "HEAD"], cwd=dashboard_root)
    print("  ✅ Dashboard data pushed successfully!")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Push prediction data to baseball-dashboard repo.")
    parser.add_argument("--date", help="Specific date to push (YYYY-MM-DD). Defaults to latest files.")
    parser.add_argument("--no-push", action="store_true",
                        help="Copy files only, don't commit or push to GitHub")
    args = parser.parse_args()

    print(f"\n🚀 Baseball Dashboard Data Bridge")
    print(f"   Source : {NCAA_API_ROOT}")
    print(f"   Target : {DASHBOARD_ROOT}")
    if args.date:
        print(f"   Date   : {args.date}")
    print()

    if not DASHBOARD_ROOT.exists():
        print(f"❌ Dashboard repo not found at: {DASHBOARD_ROOT}")
        print("   Make sure 'baseball-dashboard' exists next to 'ncaa-api'.")
        sys.exit(1)

    print(f"--- BASEBALL ---")
    copied = copy_baseball_data(date_filter=args.date)
    # cleanup_old_files(keep_days=14)
    print()

    if args.no_push:
        print("✅ Files copied. Skipping git commit (--no-push flag set).")
        return

    print("--- Git Commit & Push ---")
    git_commit_and_push(copied, DASHBOARD_ROOT)

if __name__ == "__main__":
    main()
