"""
setup_tennis_data.py
====================
Downloads historical and real-time ATP/WTA match data from Tennis-Data.co.uk.
Free, weekly-updated, no auth required.

Tennis-Data.co.uk format (ATP):
  ATP, Location, Tournament, Date, Series, Court, Surface, Round,
  Best of, Winner, Loser, WRank, LRank, WPts, LPts,
  W1, L1, W2, L2, W3, L3, Wsets, Lsets, Comment,
  B365W, B365L, MaxW, MaxL, AvgW, AvgL

Bug fixes applied:
  Bug 1: Active-year URL uses root path (no subdir) — prevents 404 on 2026.xlsx
  Bug 2: is_active_season bypasses file-exists cache — forces daily re-download
  Bug 3: _TENNIS_ROOT normalised regardless of CWD — prevents phantom tennis/tennis/ paths

Usage:
    python setup_tennis_data.py
    python setup_tennis_data.py  # run from ncaa-api/ OR ncaa-api/tennis/
"""

import os
import urllib.request
import zipfile
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Bug 3 fix: normalise root so the script works from ncaa-api/ OR ncaa-api/tennis/
# If already inside the tennis/ subdir, don't append it again.
_TENNIS_ROOT = _BASE_DIR if _BASE_DIR.endswith('tennis') else os.path.join(_BASE_DIR, 'tennis')
_ATP_DIR     = os.path.join(_TENNIS_ROOT, 'data', 'tennis_atp')
_WTA_DIR     = os.path.join(_TENNIS_ROOT, 'data', 'tennis_wta')

START_YEAR   = 2018
CURRENT_YEAR = datetime.now().year

ATP_BASE = "http://www.tennis-data.co.uk"

_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


def download_year(tour: str, year: int, dest_dir: str) -> bool:
    """
    Download one year of match data from Tennis-Data.co.uk.

    Bug 1 fix: the active/current year sits as a flat file at the server root
    (tennis-data.co.uk/2026.xlsx), not inside a year subdirectory.  Historical
    years (2018–2025) use the standard subdir layout (/2024/2024.xlsx).

    Bug 2 fix: completed historical years are cached permanently (size > 1 KB).
    The active season is NEVER skipped — the file is always re-fetched so that
    Elo ratings and profile baselines reflect this week's results.
    """
    os.makedirs(dest_dir, exist_ok=True)

    suffix      = 'w' if tour == 'WTA' else ''
    year_code   = f"{year}{suffix}"
    is_active   = (year == CURRENT_YEAR)

    for ext in ['xlsx', 'xls', 'csv']:
        dest_file = os.path.join(dest_dir, f"{year_code}.{ext}")

        # Bug 2 fix: only skip if the year is fully closed (historical).
        # Active season always re-downloads to catch new match rows.
        if not is_active and os.path.exists(dest_file) and os.path.getsize(dest_file) > 1000:
            print(f"  [SKIP] {year_code}.{ext} — historical year, already cached.")
            return True

        # Bug 1 fix: current year is a flat root file; historical years have subdirs.
        if is_active:
            url = f"{ATP_BASE}/{year_code}.{ext}"          # root: /2026.xlsx
        else:
            url = f"{ATP_BASE}/{year_code}/{year_code}.{ext}"  # subdir: /2024/2024.xlsx

        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()

            if len(content) > 500:
                with open(dest_file, 'wb') as f:
                    f.write(content)
                tag = "refreshed" if is_active else "downloaded"
                print(f"  [OK] {year_code}.{ext} {tag} ({len(content):,} bytes)")
                return True

        except Exception:
            # On active-season timeout: keep whatever we already have on disk.
            if is_active and os.path.exists(dest_file):
                print(f"  [WARN] {year_code}.{ext} fetch failed — retaining existing file.")
                return True
            if os.path.exists(dest_file):
                os.remove(dest_file)
            continue

    # ZIP archive fallback — only for historical years (active year has no zip).
    if not is_active:
        zip_url  = f"{ATP_BASE}/{year_code}/{year_code}.zip"
        zip_path = os.path.join(dest_dir, f"{year_code}.zip")
        try:
            req = urllib.request.Request(zip_url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as response:
                with open(zip_path, 'wb') as f:
                    f.write(response.read())

            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(dest_dir)
            os.remove(zip_path)

            for ext in ['xlsx', 'xls', 'csv']:
                extracted = os.path.join(dest_dir, f"{year_code}.{ext}")
                if os.path.exists(extracted) and os.path.getsize(extracted) > 500:
                    print(f"  [OK] {year_code}.{ext} extracted from zip archive.")
                    return True

        except Exception as e:
            print(f"  [FAIL] All endpoints exhausted for {year_code}: {e}")
            if os.path.exists(zip_path):
                os.remove(zip_path)

    return False


def setup_atp():
    total = CURRENT_YEAR - START_YEAR + 1
    print(f"\n=== ATP data → {_ATP_DIR} ===")
    ok = sum(download_year('ATP', y, _ATP_DIR) for y in range(START_YEAR, CURRENT_YEAR + 1))
    print(f"  ATP: {ok}/{total} datasets secured.")


def setup_wta():
    total = CURRENT_YEAR - START_YEAR + 1
    print(f"\n=== WTA data → {_WTA_DIR} ===")
    ok = sum(download_year('WTA', y, _WTA_DIR) for y in range(START_YEAR, CURRENT_YEAR + 1))
    print(f"  WTA: {ok}/{total} datasets secured.")


if __name__ == '__main__':
    print("Tennis Data Ingestion Engine — Tennis-Data.co.uk")
    print("=" * 55)
    setup_atp()
    setup_wta()
    print("\nDone. Run: python tennis/consensus_tennis.py --tour ATP")
