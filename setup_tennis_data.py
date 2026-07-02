"""
setup_tennis_data.py
====================
Downloads historical ATP/WTA match data from Tennis-Data.co.uk.
Free, weekly-updated, no auth required.

Tennis-Data.co.uk format (ATP):
  ATP, Location, Tournament, Date, Series, Court, Surface, Round,
  Best of, Winner, Loser, WRank, LRank, WPts, LPts,
  W1, L1, W2, L2, W3, L3, Wsets, Lsets, Comment,
  B365W, B365L, MaxW, MaxL, AvgW, AvgL

Note: match-level data only (no per-point serve stats).
Player serve profiles are built using implied Elo / surface win rates.

Usage:
    python setup_tennis_data.py
"""

import os
import urllib.request
import zipfile
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ATP_DIR = os.path.join(_BASE_DIR, 'tennis', 'data', 'tennis_atp')
_WTA_DIR = os.path.join(_BASE_DIR, 'tennis', 'data', 'tennis_wta')

START_YEAR = 2018
CURRENT_YEAR = datetime.now().year

# Tennis-Data.co.uk URL patterns
# ATP: http://www.tennis-data.co.uk/{year}/{year}.zip  (contains {year}.csv)
# WTA: http://www.tennis-data.co.uk/{year}w/{year}w.zip

ATP_BASE = "http://www.tennis-data.co.uk"
WTA_BASE = "http://www.tennis-data.co.uk"


def download_year(tour: str, year: int, dest_dir: str) -> bool:
    """Download one year of match data — tries xlsx, xls, csv, zip."""
    os.makedirs(dest_dir, exist_ok=True)

    suffix = 'w' if tour == 'WTA' else ''
    year_code = f"{year}{suffix}"

    # Try extensions in order of likelihood
    for ext in ['xlsx', 'xls', 'csv']:
        dest_file = os.path.join(dest_dir, f"{year_code}.{ext}")
        if os.path.exists(dest_file) and os.path.getsize(dest_file) > 1000:
            print(f"  [SKIP] {year_code}.{ext} already exists")
            return True

        url = f"{ATP_BASE}/{year_code}/{year_code}.{ext}"
        try:
            print(f"  Trying {year_code}.{ext}...")
            urllib.request.urlretrieve(url, dest_file)
            if os.path.getsize(dest_file) > 500:
                print(f"  [OK] {year_code}.{ext} ({os.path.getsize(dest_file):,} bytes)")
                return True
            os.remove(dest_file)
        except Exception:
            if os.path.exists(dest_file):
                os.remove(dest_file)
            continue

    # ZIP fallback
    zip_url = f"{ATP_BASE}/{year_code}/{year_code}.zip"
    zip_path = os.path.join(dest_dir, f"{year_code}.zip")
    try:
        print(f"  Trying {year_code}.zip...")
        urllib.request.urlretrieve(zip_url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(dest_dir)
        os.remove(zip_path)
        for ext in ['xlsx', 'xls', 'csv']:
            f = os.path.join(dest_dir, f"{year_code}.{ext}")
            if os.path.exists(f) and os.path.getsize(f) > 500:
                print(f"  [OK] via zip: {year_code}.{ext}")
                return True
    except Exception as e:
        print(f"  [FAIL] {year_code}: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)

    return False


def setup_atp():
    print(f"\n=== Downloading ATP data to {_ATP_DIR} ===")
    ok = sum(download_year('ATP', y, _ATP_DIR) for y in range(START_YEAR, CURRENT_YEAR + 1))
    print(f"  ATP: {ok}/{CURRENT_YEAR - START_YEAR + 1} years downloaded")


def setup_wta():
    print(f"\n=== Downloading WTA data to {_WTA_DIR} ===")
    ok = sum(download_year('WTA', y, _WTA_DIR) for y in range(START_YEAR, CURRENT_YEAR + 1))
    print(f"  WTA: {ok}/{CURRENT_YEAR - START_YEAR + 1} years downloaded")


if __name__ == '__main__':
    print("Tennis Data Setup — Tennis-Data.co.uk")
    print("=" * 50)
    setup_atp()
    setup_wta()
    print("\nDone. Run: python tennis/consensus_tennis.py --tour ATP")
