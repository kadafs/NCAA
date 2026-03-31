$dates = @('2026-03-26', '2026-03-27', '2026-03-28', '2026-03-29', '2026-03-30')
foreach ($d in $dates) {
    Write-Host "============================"
    Write-Host " STARTING BACKTEST: $d"
    Write-Host "============================"
    
    Write-Host "1. Running Predictor Engine..."
    python run_basketball_daily.py --mode full --date $d
    
    Write-Host "2. Running Daily Grader..."
    python grade_basketball.py --date $d
    
    Write-Host "3. Regrading Final Lines..."
    python grade_basketball.py --regrade --date $d
}

Write-Host "============================"
Write-Host " AGGREGATING RESULTS"
Write-Host "============================"
python aggregate_basketball_stats.py

Write-Host "RECALIBRATION LOOP COMPLETE!"
