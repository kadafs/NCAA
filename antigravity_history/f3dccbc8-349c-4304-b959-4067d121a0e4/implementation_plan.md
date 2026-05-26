# D1 Hybrid Model Implementation Plan
## 70% Conference Stats + 30% Full Season Stats

### Overview

This plan outlines the implementation of a hybrid prediction model for NCAA Division 1 basketball that combines conference-only statistics (70% weight) with full-season statistics (30% weight). This approach aims to balance the recency and relevance of conference play with the broader statistical context of the full season.

### Background Context

The project currently has two separate prediction models:

1. **Conference-Only Model** ([predict_d1_conf.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/predict_d1_conf.py))
   - Uses Barttorvik conference-only stats (`barttorvik_stats_conf.json`)
   - Pure conference-based analysis (conflimit=1)
   - No mixing with NCAA.com full-season data

2. **Full-Season Model** ([predict_totals.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/predict_totals.py))
   - Uses full-season Barttorvik stats (`barttorvik_stats.json`)
   - Includes NCAA.com consolidated stats
   - Broader statistical context

Both models use the `UniversalBasketballEngine` from [basketball_engine.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/core/basketball_engine.py) for prediction calculations.

### User Review Required

> [!IMPORTANT]
> **Weighting Strategy Confirmation**
> 
> The proposed 70/30 split (conference/full-season) is based on the assumption that conference play is more predictive. Please confirm:
> - Is 70% conference / 30% full-season the desired ratio?
> - Should this ratio be configurable via command-line argument or config file?
> - Should different stats (pace, efficiency, four factors) use different weights?

> [!WARNING]
> **Data Availability**
> 
> The hybrid model requires both data sources to be available:
> - `data/barttorvik_stats_conf.json` (conference-only)
> - `data/barttorvik_stats.json` (full-season)
> 
> If either is missing, the model will need a fallback strategy. Proposed fallback: use whichever data is available at 100%.

## Proposed Changes

### Core Components

#### [NEW] [predict_d1_hybrid.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/predict_d1_hybrid.py)

New prediction script that implements the hybrid model. Key features:

- **Dual Data Loading**: Load both conference-only and full-season Barttorvik stats
- **Weighted Stat Calculation**: Combine stats using 70/30 weighting formula
- **Flexible Weighting**: Support configurable weights via command-line arguments
- **Fallback Logic**: Handle missing data sources gracefully
- **Mode Support**: Maintain compatibility with `safe` and `full` prediction modes
- **Trace Logging**: Show which data sources and weights were used

**Weighted Stat Formula**:
```
hybrid_stat = (conf_stat × 0.70) + (full_stat × 0.30)
```

Applied to all key metrics:
- `adj_off` (Adjusted Offensive Efficiency)
- `adj_def` (Adjusted Defensive Efficiency)
- `adj_t` (Adjusted Tempo)
- `efg`, `efg_d` (Effective Field Goal %)
- `to`, `to_d` (Turnover %)
- `or`, `or_d` (Offensive Rebound %)
- `ftr`, `ftr_d` (Free Throw Rate)

---

### Utility Functions

#### [MODIFY] [utils/mapping.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/utils/mapping.py)

Add a new utility function for weighted stat calculation:

```python
def calculate_weighted_stats(conf_stats, full_stats, conf_weight=0.70):
    """
    Combine conference and full-season stats with specified weights.
    
    Args:
        conf_stats: Conference-only stats dict
        full_stats: Full-season stats dict
        conf_weight: Weight for conference stats (default 0.70)
    
    Returns:
        Dict with weighted stats
    """
```

This centralizes the weighting logic for reuse across different models.

---

### Configuration

#### [MODIFY] [configs/leagues/ncaa.json](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/configs/leagues/ncaa.json)

Add hybrid model configuration:

```json
{
  "hybrid_model": {
    "conference_weight": 0.70,
    "full_season_weight": 0.30,
    "require_both_sources": false,
    "fallback_to_available": true
  }
}
```

This allows easy adjustment of weights without code changes.

---

### Data Files

The hybrid model will use existing data files:

- **Input**: `data/barttorvik_stats_conf.json` (conference-only stats)
- **Input**: `data/barttorvik_stats.json` (full-season stats)
- **Output**: `data/d1_hybrid_predictions.json` (prediction results)

No new data fetching required - both sources are already maintained by existing scripts.

---

### Integration Points

#### Command-Line Interface

```bash
# Run with default 70/30 weights
python ncaa/predict_d1_hybrid.py --mode safe

# Custom weights
python ncaa/predict_d1_hybrid.py --mode full --conf-weight 0.80 --full-weight 0.20

# Specific date
python ncaa/predict_d1_hybrid.py --date 2026-02-17 --trace
```

#### Output Format

Predictions will include metadata showing the hybrid approach:

```json
{
  "matchup": "Michigan @ Purdue",
  "model_total": 145.19,
  "edge": -11.31,
  "decision": "PLAY",
  "mode": "A",
  "confidence": "HIGH",
  "data_sources": {
    "conference_weight": 0.70,
    "full_season_weight": 0.30,
    "both_available": true
  }
}
```

## Verification Plan

### Automated Tests

1. **Data Loading Test**
   ```bash
   python ncaa/predict_d1_hybrid.py --date 2026-02-17 --trace
   ```
   - Verify both data sources load successfully
   - Check weighted stat calculations are correct
   - Confirm fallback logic works when data is missing

2. **Comparison Test**
   ```bash
   # Generate predictions from all three models
   python ncaa/predict_d1_conf.py --date 2026-02-17 > conf_results.txt
   python ncaa/predict_totals.py > full_results.txt
   python ncaa/predict_d1_hybrid.py --date 2026-02-17 > hybrid_results.txt
   ```
   - Compare model totals across all three approaches
   - Verify hybrid predictions fall between conference-only and full-season
   - Analyze edge differences and decision changes

3. **Weight Sensitivity Test**
   ```bash
   # Test different weight combinations
   python ncaa/predict_d1_hybrid.py --conf-weight 0.50 --full-weight 0.50
   python ncaa/predict_d1_hybrid.py --conf-weight 0.80 --full-weight 0.20
   python ncaa/predict_d1_hybrid.py --conf-weight 0.90 --full-weight 0.10
   ```
   - Verify predictions change appropriately with different weights
   - Ensure weights sum to 1.0 (validation check)

### Manual Verification

1. **Spot Check Calculations**
   - Manually verify weighted stat calculations for 2-3 games
   - Compare against expected values using calculator
   - Ensure four factors are weighted correctly

2. **Edge Case Testing**
   - Test with only conference data available
   - Test with only full-season data available
   - Test with mismatched team names between sources

3. **Output Validation**
   - Verify JSON output is valid and complete
   - Check trace logs show correct data sources
   - Confirm predictions are saved to correct file

### Success Criteria

- ✅ Hybrid model successfully loads and combines both data sources
- ✅ Weighted calculations produce reasonable predictions
- ✅ Predictions fall logically between conference-only and full-season models
- ✅ Fallback logic works when data sources are unavailable
- ✅ Configuration and command-line arguments work as expected
- ✅ Output format is consistent with existing models
