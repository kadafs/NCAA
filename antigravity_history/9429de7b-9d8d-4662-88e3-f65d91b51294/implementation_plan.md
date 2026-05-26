# Implementation Plan: Model v2.1 Architecture Refinement

Strictly align the `UniversalBasketballEngine` with formalized mathematical principles by correcting the order of operations and standardizing nomenclature.

## Proposed Changes

### [Component] Basketball Engine
- **[MODIFY] [basketball_engine.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/core/basketball_engine.py)**:
    - **Step Ordering**: Refactor the flow to follow the sequence:
        1.  **Matchup**: Compute $Exp\_Eff_A$ and $Exp\_Eff_H$ (Symmetric).
        2.  **Pace**: Apply $\frac{Pace}{100}$ scaling to reach $Raw\_Game\_Total$.
        3.  **HCA**: Apply $hca\_total\_bump$ to the $Raw\_Game\_Total$.
        4.  **Regression**: Apply $\beta = 0.94$ to the aggregated result.
    - **Terminology**: Update `_log` statements to be consistent: "Regression: Applied (beta=0.94)".
    - **Cleaning**: Ensure legacy "Step 4" and market blocks are cleanly bypassed or integrated without conflict.

---

### [Component] Documentation
- **[MODIFY] [prediction_models_logic.md](file:///C:\Users\markk\.gemini\antigravity\brain\9429de7b-9d8d-4662-88e3-f65d91b51294\prediction_models_logic.md)**: 
    - Make the "Hidden Scaling" (Pace) explicit in the formula.
    - Formally define the order of operations: $Total_{Final} = \beta \cdot (Total_{Raw} + HCA)$.

## Verification Plan

### Automated Tests
- Run `run_basketball_daily.py --trace` and verify the mathematical chain:
    - $Raw = (Eff_A + Eff_H) * (Pace / 100)$
    - $Adjusted = Raw + HCA$
    - $Final = Adjusted * 0.94$
