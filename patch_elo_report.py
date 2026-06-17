"""Patch script: fixes elo_delta_report unpacking in main() of run_wc2026.py."""
import pathlib, sys

f = pathlib.Path("run_wc2026.py")
lines = f.read_text(encoding="utf-8").splitlines(keepends=True)

# Find the elo_report block by looking for the for-loop line that needs fixing
target_for = "        for team, base, live_v, delta in deltas:\n"
target_for_r = "        for team, base, live_v, delta in deltas:\r\n"

patched = False
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if line in (target_for, target_for_r):
        # Replace the old 3-line block (for + bar + trend + print) with new 5-line block
        eol = "\r\n" if "\r\n" in line else "\n"
        new_lines.append(f"        for team, base, live_v, live_delta, conf, eff, cadj in deltas:{eol}")
        new_lines.append(f"            live_trend = (f\"+{{live_delta}}\" if live_delta > 0{eol}")
        new_lines.append(f"                          else (str(live_delta) if live_delta < 0 else \"=\")){eol}")
        new_lines.append(f"            cadj_str   = f\"{{cadj:+d}}\" if cadj != 0 else \"  0\"{eol}")
        new_lines.append(f"            print(f\"  {{team:<28}}  {{conf:<8}}  {{base:>5}}  {{live_v:>5}}  {{cadj_str:>5}}  {{eff:>5}}  {{live_trend}}\"){eol}")
        # Skip the old 3 lines (bar, trend, print)
        i += 1  # skip old for line - already replaced
        while i < len(lines) and lines[i].strip() not in ("", "print()", "return"):
            i += 1
        # DON'T skip the print() and return - they still stay
        patched = True
        continue

    # Also fix the header lines inside elo_report block
    if "ELO DELTA REPORT" in line:
        eol = "\r\n" if "\r\n" in line else "\n"
        new_lines.append(f"        print(f\"\\n  ELO REPORT  ({{games_played}} games processed, K=40)\"){eol}")
        new_lines.append(f"        print(f\"  Sorted by Effective Elo (true predicted strength)\\n\"){eol}")
        new_lines.append(f"        print(f\"  {{' ':<28}}  {{'Conf':<8}}  {{'Base':>5}}  {{'Live':>5}}  {{'Adj':>5}}  {{'Eff':>5}}  Trend\"){eol}")
        new_lines.append(f"        print(f\"  {{'-'*80}}\"){eol}")
        # skip old 3 header lines
        i += 1
        i += 1  # skip ─*62 line 1
        i += 1  # skip Team/Base/Live/Delta line
        i += 1  # skip ─*62 line 2
        patched = True
        continue

    new_lines.append(line)
    i += 1

if patched:
    f.write_text("".join(new_lines), encoding="utf-8")
    print("PATCHED OK")
else:
    print("ERROR: target line not found")
    sys.exit(1)
