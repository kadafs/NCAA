$dates = @('2026-03-26', '2026-03-27', '2026-03-28', '2026-03-29', '2026-03-30')
$env:PYTHONIOENCODING="utf-8"
foreach ($d in $dates) {
    Write-Host "============================"
    Write-Host " GRADING DATE: $d"
    Write-Host "============================"
    
    Write-Host "1. Initial Grade..."
    python grade_basketball.py --date $d
    
    Write-Host "2. Regrade (Closing Lines)..."
    python grade_basketball.py --regrade --date $d
    
    Write-Host "3. Final Aggregation Step..."
    python aggregate_basketball_stats.py
    
    Write-Host "4. Syncing $d to Dashboard..."
    python push_to_dashboard.py --sport basketball --date $d
}

Write-Host "ALL GRADING AND AGGREGATION COMPLETE!"
