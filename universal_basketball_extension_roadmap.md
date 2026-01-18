# Masterplan: Universal Basketball Extension (v1.3 Unified)

## 1. Recommendation: EuroLeague & WNBA
To maximize the "Edge" of our deterministic model, I recommend expanding in this order:
1.  **EuroLeague**: High-discipline, tactical play where efficiency-based math is most effective.
2.  **WNBA**: High market inefficiency (softer lines) and data stability.

---

## 2. Technical Roadmap: The Unified Architecture

### Phase 1: The "Physics" Engine Core
We move away from `nba/v1_2/engine.py` and `ncaa/v1_2/engine.py`. We create a single, high-discipline core.

- **`core/basketball_engine.py`**: A universal class that takes a `LeagueConfig` and a `GameInput`.
- **The Core Formula**: Always uses `((Eff_Avg * Pace_Avg) / 100) * 2`. 
- **Time Scaling**: The engine automatically detects if the game is **40 mins** (FIBA/NCAA/WNBA) vs **48 mins** (NBA) and applies a `TIME_FACTOR` (1.0 vs 1.2) to the pace calculations.

---

### Phase 2: Configuration-Driven Gravity
We create `configs/leagues/` containing JSON profiles for every league.

| Constant | NBA (48m) | EuroLeague (40m) | NCAA (40m) |
| :--- | :--- | :--- | :--- |
| **Pace Pivot** | 100.0 | 72.0 | 68.0 |
| **Eff Pivot** | 115.0 | 110.0 | 105.0 |
| **Regression** | 0.96x | 0.95x | 0.97x |
| **HCA Bump** | +2.5 | +2.8 | +3.5 |

---

### Phase 3: The Unified Population Layer
We create a `DataBridge` that translates any raw JSON (BartTorvik, NBA API, Euro stats) into a standard **StandardizedInputSheet**:
- `teamA_off`, `teamA_def`, `teamA_pace`
- `teamB_off`, `teamB_def`, `teamB_pace`
- `is_neutral_site` (Essential for NCAA/Euro playoffs)
- `days_rest` (For fatigue modeling)

---

### Phase 4: The Multi-League CLI Runner
A single entry point for the whole project:
```powershell
python -m run --league euro --mode full --trace
python -m run --league nba --mode safe
```

---

## 3. Implementation Steps
1. **Directory Restructuring**: Move shared logic to a `/core` directory.
2. **Config Initialization**: Create the JSON profiles for NBA and NCAA first to ensure backward compatibility.
3. **Refactor TotalsEngine**: Remove all sport-specific constants from the engine class; make it strictly a math processor.
4. **Refactor PropEngine**: Create a positional mapping system that works for "Euro/FIBA" positions (which can differ slightly from NBA roles).
