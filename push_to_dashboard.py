#!/usr/bin/env python3
"""
push_to_dashboard.py
────────────────────
Option A Data Bridge: copies freshly generated prediction files from ncaa-api
into the Sports Analytics dashboard repository, then commits and pushes to GitHub.

Usage:
    # After running run_football_daily.py or run_basketball_daily.py, call:
    python push_to_dashboard.py --sport football
    python push_to_dashboard.py --sport basketball
    python push_to_dashboard.py --sport all
    
    # With a specific date override:
    python push_to_dashboard.py --sport football --date 2026-03-30
"""

import os
import sys
import shutil
import subprocess
import argparse
from datetime import date
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
# Paths — adjust if your folders are in a different location
NCAA_API_ROOT   = Path(__file__).parent
DASHBOARD_ROOT  = NCAA_API_ROOT.parent / "Sports Analytics"

SPORTS = ["football", "basketball"]

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


def copy_sport_data(sport: str, date_filter: str | None = None):
    """
    Copy prediction files for a sport from ncaa-api/data/{sport}
    into Sports Analytics/public/data/{sport}.
    
    If date_filter is provided (YYYY-MM-DD), only copies that date's file.
    Otherwise copies the latest file.
    """
    src_dir  = NCAA_API_ROOT / "data" / sport
    dest_dir = DASHBOARD_ROOT / "public" / "data" / sport

    if not src_dir.exists():
        print(f"  ⚠️ Source directory not found: {src_dir}")
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Find files to copy
    all_files = sorted(src_dir.glob("universal_predictions_*.json"), reverse=True)
    if not all_files:
        print(f"  ⚠️ No prediction files found in {src_dir}")
        return []

    if date_filter:
        files_to_copy = [f for f in all_files if date_filter in f.name]
        if not files_to_copy:
            print(f"  ⚠️ No file found for date {date_filter} in {src_dir}")
            return []
    else:
        # Copy only the most recent file
        files_to_copy = [all_files[0]]

    copied = []
    for src_file in files_to_copy:
        dest_file = dest_dir / src_file.name
        print(f"  📄 Copying: {src_file.name}")
        shutil.copy2(src_file, dest_file)
        copied.append(src_file.name)

    # Also copy leaderboard files if they exist
    for lb_pattern in ["leaderboard.json", "team_leaderboard.json"]:
        lb_src = src_dir / lb_pattern
        if lb_src.exists():
            shutil.copy2(lb_src, dest_dir / lb_pattern)
            print(f"  📄 Copying: {lb_pattern}")

    print(f"  ✅ Copied {len(copied)} file(s) for {sport}.")
    return copied


def cleanup_old_files(sport: str, keep_days: int = 14):
    """
    Remove universal_predictions_*.json files older than keep_days
    from the dashboard repo to prevent git history from ballooning.
    """
    from datetime import timedelta
    dest_dir = DASHBOARD_ROOT / "public" / "data" / sport
    if not dest_dir.exists():
        return

    cutoff = date.today() - timedelta(days=keep_days)
    removed = []
    for f in dest_dir.glob("universal_predictions_*.json"):
        date_str = f.stem.replace("universal_predictions_", "")
        try:
            file_date = date.fromisoformat(date_str)
            if file_date < cutoff:
                f.unlink()
                removed.append(f.name)
        except ValueError:
            pass  # skip files with unexpected naming

    if removed:
        print(f"  🗑️  Cleaned up {len(removed)} old {sport} file(s): {', '.join(removed)}")
    else:
        print(f"  ✅ No old {sport} files to clean up (keeping last {keep_days} days).")


def git_commit_and_push(copied_files: dict[str, list[str]], dashboard_root: Path):
    """Stage changed files, create a commit, and push to GitHub."""

    # Check if it's a git repo
    git_dir = dashboard_root / ".git"
    if not git_dir.exists():
        print("\n  ⚠️  Sports Analytics is not a Git repository yet.")
        print("  Run:  cd \"Sports Analytics\" && git init && git remote add origin <YOUR_REPO_URL>")
        print("  Then re-run this script.")
        return

    # Stage all changes in public/data
    run(["git", "add", "public/data/"], cwd=dashboard_root)

    # Build descriptive commit message
    summary_parts = []
    for sport, files in copied_files.items():
        if files:
            summary_parts.append(f"{sport}: {', '.join(files)}")
    
    if not summary_parts:
        print("  ℹ️  Nothing new to commit.")
        return

    today = date.today().isoformat()
    commit_msg = f"data: push predictions {today} — " + " | ".join(summary_parts)

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
    run(["git", "push"], cwd=dashboard_root)
    print("  ✅ Dashboard data pushed successfully!")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Push prediction data to Sports Analytics dashboard repo.")
    parser.add_argument("--sport", choices=["football", "basketball", "all"], default="all",
                        help="Which sport's data to push")
    parser.add_argument("--date", help="Specific date to push (YYYY-MM-DD). Defaults to latest file.")
    parser.add_argument("--no-push", action="store_true",
                        help="Copy files only, don't commit or push to GitHub")
    args = parser.parse_args()

    target_sports = SPORTS if args.sport == "all" else [args.sport]

    print(f"\n🚀 Sports Analytics Data Bridge")
    print(f"   Source : {NCAA_API_ROOT}")
    print(f"   Target : {DASHBOARD_ROOT}")
    if args.date:
        print(f"   Date   : {args.date}")
    print()

    if not DASHBOARD_ROOT.exists():
        print(f"❌ Dashboard repo not found at: {DASHBOARD_ROOT}")
        print("   Make sure 'Sports Analytics' exists next to 'ncaa-api'.")
        sys.exit(1)

    all_copied = {}
    for sport in target_sports:
        print(f"--- {sport.upper()} ---")
        copied = copy_sport_data(sport, date_filter=args.date)
        all_copied[sport] = copied
        cleanup_old_files(sport, keep_days=14)
        print()

    if args.no_push:
        print("✅ Files copied. Skipping git commit (--no-push flag set).")
        return

    print("--- Git Commit & Push ---")
    git_commit_and_push(all_copied, DASHBOARD_ROOT)


if __name__ == "__main__":
    main()
