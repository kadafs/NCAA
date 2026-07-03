# Tennis & Cricket Model Reference + Daily Maintenance Workflows

---

## PART 1 — TENNIS MODEL

### Architecture Overview

The tennis model is a **three-layer stack**: historical data ingest → per-player serve profile construction → Markov-chain + Monte Carlo match simulation.

```
Tennis-Data.co.uk Excel sheets  (2018–2026)
         ↓
  fetch_tennis_stats.py          (data layer)
         ↓
  surface_engine.py              (surface + constants)
         ↓
  tennis_markov.py               (simulation engine)
         ↓
  consensus_tennis.py            (edge detection + report)
```

---

### Layer 1 — Data Ingest: `fetch_tennis_stats.py`

**Source:** Tennis-Data.co.uk `.xlsx` files — no API key, no commercial dependency.

**What it loads:**
- ATP: `tennis/data/tennis_atp/YYYY.xlsx` (e.g., `2026.xlsx`)
- WTA: `tennis/data/tennis_wta/YYYYw.xlsx` (e.g., `2026w.xlsx`)
- Years covered: **2018 → present** (configurable `min_year`)

**Key functions:**

| Function | Purpose |
|----------|---------|
| `_load_match_data(tour)` | Reads + concatenates all yearly sheets; quarantines retirements |
| `normalize_tennis_name(name)` | Canonical `surname-initial` key (immune to accents, dots, multi-word surnames) |
| `build_player_serve_profile(name, tour, surface)` | Returns full serve/return dict for any player |

**Name normalization pipeline** (`normalize_tennis_name`):
1. Strip Unicode accents via NFD decomposition
2. Pre-clean alias check (before dot stripping — catches `M.Berrettini`)
3. Strip non-alphanumeric, lowercase, collapse spaces
4. Post-clean alias check (`TOP_50_ALIASES` map)
5. Multi-word surname detection via `SURNAME_PREFIXES = {de, del, van, von, di, le}`
   - Scenario A: `De Minaur A.` → last token is single char → `de minaur-a`
   - Scenario B: `Alex de Minaur` → prefix at any position → `de minaur-a`
   - Scenario C: `Jannik Sinner` → standard → `sinner-j`

**Retirement quarantine:**
All rows where the `Comment` column matches `Retired|Walkover|W/O|Def.|Default` are filtered **before** Elo or profile calculation. Retirement counts and match counts are tallied in a **single combined pass** to avoid multi-call inflation.

**Profile build logic** (`build_player_serve_profile`):
1. Filter historical matches to the requested **surface** (Grass/Clay/Hard)
2. Run **Elo ladder** over those matches (K=32, initial=1500, K-factor reduces by tier)
3. Bayesian shrinkage blends player's surface win rate with league prior (volume-weighted)
4. Bisection solver: iterates `p` until `p_server_wins_game(p) == target_hold_rate`
5. Returns: `first_serve_pct`, `first_serve_win_pct`, `second_serve_win_pct`, `return_points_won_pct`, `_implied_serve_prob`, `observed_win_rate`, `retirement_risk_pct`

---

### Layer 2 — Surface Constants: `surface_engine.py`

**Single source of truth** for all surface/format parameters. Nothing is redefined in the simulation engine.

| Constant | ATP | WTA |
|----------|-----|-----|
| `LEAGUE_HOLD` | 0.800 | 0.620 |
| `LEAGUE_POINT_PROB` | 0.633 | 0.549 |

**Surface modifiers** (`SURFACE_MODIFIERS`) are **multiplicative** in **log-odds space** — never raw probability space:
```
raw_odds = p / (1-p)
adj_odds = raw_odds × surface_mod
server_adj = adj_odds / (1 + adj_odds)
```

| Surface | ATP mod | WTA mod |
|---------|---------|---------|
| Grass | 1.20 | 1.15 |
| Hard | 1.00 | 1.00 |
| Clay | 0.88 | 0.90 |

> Applying 1.20 to a raw probability (0.679 × 1.20 = 0.815) violates the [0,1] boundary.
> Applying to odds (2.115 × 1.20 = 2.538 → 0.717) is always bounded.

**Format routing** (`sets_to_win`):
- Grand Slam + ATP Finals → Bo5 (returns `3`)
- All other events → Bo3 (returns `2`)

---

### Layer 3 — Simulation Engine: `tennis_markov.py`

**Two analytical stages + one Monte Carlo stage:**

#### Point → Game (Analytical)
```python
p_server_wins_game(p):
    q = 1 - p
    deuce = 20.0 × p³ × q³               # P(reach deuce)
    win_deuce = p² / (1 - 2pq)            # P(win from deuce)
    return p⁴ + 4p⁴q + 10p⁴q² + deuce × win_deuce
```
Calibrated constants: ATP `p=0.633 → hold 0.800`, WTA `p=0.549 → hold 0.621`

#### Point Probability Blend (`blended_serve_win_prob`)
```
1. raw_serve = FSP × FSW + (1-FSP) × SSW
2. Apply surface modifier in LOG-ODDS space
3. returner_adj = 1 - returner_rpw
4. s_point = server_adj^0.55
   r_point = returner_adj^0.55
   l_point = league_hold^0.55
5. result = log_odds_blend(s_point, r_point, l_point)
```
The 0.55 power compress maps all inputs to a consistent scale before blending.

#### Set & Match (Monte Carlo, 10,000 iterations)
**Tiebreak server routing:**
```python
seq = ((total_pts + 1) // 2) % 2          # 0=first server, 1=second server
is_p1_serving = where(p1_serves_first, seq==0, seq==1)
p_win = where(is_p1_serving, p_p1_serve, 1 - p_p2_serve)
```

**Set server alternation** (game_num-based, not simple flip):
```python
# After each set:
set_games_odd = (game_num % 2 == 1)
p1_serves_first[idx] = where(set_games_odd, ~p1_start_mask, p1_start_mask)
```
Handles: 6-4 (10 games, even → same starter), 6-3 (9 games, odd → flip), 7-6 TB (13 games after `game_num += 1` in TB block → flip).

**Simulation outputs:**
- `p1_match_win_prob`, `p2_match_win_prob`
- `p1_first_set_win_prob`
- `expected_total_games`
- `over_*/under_*_prob` for 20.5 / 21.5 / 22.5 / 23.5 / 24.5 game lines
- `p1_wins_2_0_prob`, `p1_wins_2_1_prob` (set scores)
- `raw_game_distribution` (full array for custom line analysis)

---

### Layer 4 — Report: `consensus_tennis.py`

**Edge detection** (`_detect_edge`):
- Total games O/U: flags if model prob ≥ 60%
- Match winner: flags if ≥ 60%
- First set winner: flags if ≥ 58%
- Confidence: `High` if any edge ≥ 10%, else `Medium`

**Report output** (`_write_report`):
- Format computed via `sets_to_win()` — never reads `sim['sets_to_win']`
- Hold rate computed from `p_server_wins_game(p1p['_implied_serve_prob'])` — decoupled from sim diagnostics
- Over lines as `1 - under_prob` with `.get()` fallbacks
- Retirement void flag for O/U when `retirement_risk_flag` is set

---

## PART 2 — CRICKET MODEL

### Architecture Overview

The cricket model is a **ball-by-ball vectorized T20 innings simulator**. It runs 10,000 parallel innings simultaneously using NumPy arrays.

```
fetch_cricket_stats.py    (player + team profile builder)
ground_factors.py         (venue run-scaling factors)
monte_carlo_t20.py        (vectorized innings simulator)
consensus_t20.py          (match assembly + edge detection + report)
```

---

### Simulation Core: `monte_carlo_t20.py`

#### League Baselines

| Event | Rate |
|-------|------|
| Dot ball | 38.0% |
| Single/2 | 36.0% |
| Boundary (4/6) | 15.5% |
| Wicket | 4.8% |
| Wide/No-ball | 4.0% |

#### Delivery Resolution — Per Ball

**Five mutually exclusive events per ball:**

1. **Wicket** → batter dismissed, next man in
2. **Extra** (wide/no-ball) → +1 run, over_balls NOT incremented (key rule)
3. **Dot** → 0 runs
4. **Boundary** → 4 or 6 runs (random split weighted by batter profile)
5. **Single/2** → 1 or 2 runs + striker rotation on odd runs

**Log-odds blend per event:**
```python
log_odds_blend(bowler_rate, batter_rate, league_rate)
```
Bowler and batter rates are combined against the league baseline — exactly the same formulation as the tennis engine.

#### Four Structural Fixes Built-In

1. **Striker rotation**: odd-run deliveries rotate striker ↔ non-striker; over-end always swaps
2. **Wide/no-ball guard**: extras don't advance `over_balls` counter — no artificial over truncation
3. **Settled-in boost** (inverse TTTO): after 10 balls faced, `boundary_pct` climbs and `dot_pct` falls (capped at +35% after ~33 balls)
4. **Powerplay extraction**: overs 1–6 tracked separately for PP runs market

#### Ground Factors: `ground_factors.py`

```python
GROUND_FACTORS = {
    'Wankhede Stadium':  {'factor': 1.08, 'dew': True,  'pitch': 'batting', 'avg_score': 178},
    "Lord's":            {'factor': 0.93, 'dew': False, 'pitch': 'bowling', 'avg_score': 153},
    ...  # 24 venues covering IPL, BBL, The Hundred, PSL, international
}
```

`ground_factor` scales boundary rates multiplicatively: small grounds → more sixes → higher factor.

**Dew modifier**: `DEW_FACTOR_MODIFIER = 1.07` — applied to batting team's boundary rate in 2nd innings during evening matches in subcontinent/Asia.

#### Match Assembly

Full T20 match = two innings:
1. Innings 1 → `simulate_innings_vectorized(is_chasing=False)` → team 1 total distribution
2. Innings 2 → `simulate_innings_vectorized(is_chasing=True)` → team 2 chase distribution
3. Match winner = `team2_score > team1_score` across all iterations

**Outputs per match:**
- `p1_win_prob`, `p2_win_prob`
- `expected_total_runs` (both innings combined)
- `expected_powerplay_runs_t1`, `expected_powerplay_runs_t2`
- `expected_wickets_t1`, `expected_wickets_t2`
- O/U line probabilities for total runs (e.g., over/under 330.5, 345.5, 360.5)

---

## PART 3 — DAILY MAINTENANCE WORKFLOWS

### Tennis Daily Workflow

```powershell
# Step 1 — Refresh in-season data (always re-downloads current year)
python setup_tennis_data.py

# Step 2 — Run ATP predictions
python tennis/consensus_tennis.py --tour ATP --iterations 10000

# Step 3 — Run WTA predictions
python tennis/consensus_tennis.py --tour WTA --iterations 10000

# Step 4 — Both tours in one pass
python tennis/consensus_tennis.py --tour BOTH
```

**Output files:**
- `tennis/data/tennis_atp_report_YYYY-MM-DD.md` — ATP markdown report
- `tennis/data/tennis_wta_report_YYYY-MM-DD.md` — WTA markdown report
- `tennis/data/tennis_atp_predictions_YYYY-MM-DD.json` — JSON bridge for dashboard
- `tennis/data/tennis_wta_predictions_YYYY-MM-DD.json`

**Key flags:**
- `--iterations 50000` — higher precision for Wimbledon/Slam semifinals
- Default 10,000 = ~3–5 seconds per match

**Data cache behaviour:**
- Historical years (2018–2025): skipped if file > 1KB (stable)
- Current year (2026): **always re-downloaded** regardless of file existence

---

### Cricket Daily Workflow

```powershell
# Run T20 predictions for The Hundred or any T20 league
python cricket/consensus_t20.py

# Override for specific tournament
python cricket/consensus_t20.py --tournament "The Hundred" --iterations 10000
```

**Output files:**
- `cricket/data/t20_report_YYYY-MM-DD.md`
- `cricket/data/t20_predictions_YYYY-MM-DD.json`

---

### Other Sport Workflows (Existing)

**Baseball (MLB / KBO / NPB):**
```powershell
python mlb/consensus_f5.py                    # MLB F5 morning picks
python mlb/consensus_f5_v3.py                 # V3: Top-Down + Tuned MC + Weather
python kbo/consensus_f5_kbo.py                # KBO F5 morning picks
python npb/consensus_f5_npb.py                # NPB F5 morning picks
python mlb/grade_td_reports.py                # MLB grader
python grade_intl_reports.py --league KBO     # KBO grader
```

**Basketball:**
```powershell
# 1. Update raw stats from Proballers
python scrape_proballers.py --daily today --cutoff_date 2026-02-02

# 2. Rebuild True Offense/Defense Matrix
python generate_advanced_metrics.py

# 3. Run today's predictions
python run_basketball_daily.py --mode full --date 2026-07-02 --refresh

# 4. Push to dashboard
python push_to_dashboard.py --sport basketball

# 5. Daily confidence report
python run_confidence_report.py
python run_confidence_report.py --min_score 60      # high-confidence only
python run_confidence_report.py --min_graded 7      # min 7 graded games each
python run_confidence_report.py --components        # show V/M/B/S breakdown
python run_confidence_report.py --hidden_gems       # value picks below radar
```

**Football:**
```powershell
# Uses /basketball_daily, /football_daily, /nbl1_daily slash commands
python run_football_daily.py
python grade_football.py
```

---

## Quick Reference — Key Files

| File | Role |
|------|------|
| [setup_tennis_data.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/setup_tennis_data.py) | Downloads/refreshes all ATP+WTA xlsx files |
| [tennis/fetch_tennis_stats.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/tennis/fetch_tennis_stats.py) | Historical data → player profiles |
| [tennis/surface_engine.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/tennis/surface_engine.py) | League constants, surface modifiers, format routing |
| [tennis/tennis_markov.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/tennis/tennis_markov.py) | Markov game model + Monte Carlo set/match |
| [tennis/consensus_tennis.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/tennis/consensus_tennis.py) | Edge detection + markdown/JSON report |
| [cricket/monte_carlo_t20.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/cricket/monte_carlo_t20.py) | Vectorized T20 innings simulator |
| [cricket/ground_factors.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/cricket/ground_factors.py) | Venue run factors + dew modifier |
| [cricket/fetch_cricket_stats.py](file:///c:/Users/markk/OneDrive/Desktop/CODE\ncaa-api/cricket/fetch_cricket_stats.py) | Player/team stat builder |
| [cricket/consensus_t20.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/cricket/consensus_t20.py) | T20 match assembly + edge detection |
| [Maintenance Workflow- 2.txt](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/Maintenance%20Workflow-%202.txt) | Full legacy workflow reference |
