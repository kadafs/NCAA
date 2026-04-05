import subprocess
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Worst-offending league IDs from audit (AVG delta > 14, systematic bias)
leagues = [
    (228, "1. Liga"),
    (41,  "DBBL Women"),
    (212, "NBL1 Central"),
    (64,  "Prva A Liga"),
    (267, "SBL"),
    (2,   "LNB"),
    (210, "NBL1 South Women"),
    (198, "ABA League"),
    (34,  "Basketligaen"),
    (33,  "ZBL W"),
    (30,  "Premijer liga"),
    (48,  "Premier league"),
    (85,  "First League"),
    (265, "1. ZLS Women"),
    (76,  "BSN"),
    (368, "BNXT League"),
    (8,   "Pro B"),
    (255, "WBL Women"),
    (99,  "Superettan"),
    (92,  "WKBL W"),
    (89,  "Liga Nova KBM"),
    (201, "FIBA Europe Cup"),
    (211, "NBL1 Central Women"),
]

ok, failed = [], []
for lid, name in leagues:
    print(f"\n--- Calibrating {name} (ID: {lid}) ---")
    result = subprocess.run(
        [sys.executable, "calibrate_from_local.py", "--league_id", str(lid)],
        capture_output=False
    )
    if result.returncode == 0:
        ok.append(f"{name} ({lid})")
    else:
        failed.append(f"{name} ({lid})")

print("\n" + "="*60)
print(f"  Done: {len(ok)} succeeded | {len(failed)} failed")
if failed:
    print(f"  Failed: {', '.join(failed)}")
