# Daily SDI Report

I have successfully created and tested the `run_daily_sdi_report.py` script. This tool allows you to instantly scan any daily prediction slate and rank the matches based on their Star Player Dependency Index (SDI).

## Usage
You can run the script directly from your terminal:
```bash
python run_daily_sdi_report.py
```
This will automatically default to today's date and scan the `universal_predictions_{TODAY}.json` file.

To check historical dates or future dates, simply pass the `--date` flag:
```bash
python run_daily_sdi_report.py --date 2026-05-04
```

## What it shows you

> [!TIP]
> The script calculates a **Combined SDI** for each match by taking the average of the Home Team's SDI and the Away Team's SDI. 

It splits the slate into three distinct sections:
1. **Most Volatile Matches**: These are matches where both teams are heavily reliant on 1-2 star players (Highest Combined SDI). These games carry the highest variance, as an injury, ejection, or simply an off-night for a star player will drastically swing the final score.
2. **Safest Volume Matches**: These are matches where both teams are highly balanced (Lowest Combined SDI). Because scoring is distributed across the roster, these games are much safer for flat-floor or volume-based prediction strategies.
3. **Individual Red Flags**: Regardless of the combined match score, the script will isolate and flag any *single team* playing today that has a critically high dependency (> 55% SDI).

## Verification
I ran a test against today's slate (`2026-05-05`) and it correctly loaded the 55 predictions, seamlessly cross-referenced them with the SDI index (including automatically resolving Women's teams with the " W" suffix mapping), and printed out a clean ranked table!
