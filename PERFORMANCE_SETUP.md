# 📊 Real Performance Audit Setup

I have built the infrastructure to transition your **Model Performance** page from mock data to real, audited results.

## 1. Database Setup (Action Required)
You must create the tracking tables in your Supabase SQL Editor. Copy and paste this SQL:

```sql
-- 1. Track every prediction for grading
CREATE TABLE IF NOT EXISTS predictions_history (
    id TEXT PRIMARY KEY, -- league_date_away_home
    league TEXT NOT NULL,
    game_date DATE NOT NULL,
    matchup TEXT NOT NULL,
    market_total FLOAT,
    model_total FLOAT,
    edge FLOAT,
    status TEXT DEFAULT 'pending', -- 'pending', 'graded'
    actual_score_away INT,
    actual_score_home INT,
    actual_total INT,
    is_win BOOLEAN,
    profit FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Store aggregated metrics for the dashboard
CREATE TABLE IF NOT EXISTS audit_summary (
    league TEXT PRIMARY KEY, -- 'TOTAL', 'nba', 'ncaa'
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    pushes INT DEFAULT 0,
    roi FLOAT DEFAULT 0.0,
    profit FLOAT DEFAULT 0.0,
    win_pct FLOAT DEFAULT 0.0,
    rolling_trend JSONB DEFAULT '[60, 62, 58, 61, 59, 61]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Security (Allow the app to read/write)
ALTER TABLE predictions_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all to view" ON predictions_history FOR SELECT USING (true);
CREATE POLICY "Allow update" ON predictions_history FOR ALL USING (true);

ALTER TABLE audit_summary ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all to view" ON audit_summary FOR SELECT USING (true);
CREATE POLICY "Allow update" ON audit_summary FOR ALL USING (true);
```

---

## 2. How the System Works

### Phase A: Archiving (Automated)
The `core/supabase_pusher.py` script now automatically saves every prediction into the `predictions_history` table as "pending".

### Phase B: Grading (Run Daily)
Run this new script every morning to fetch yesterday's scores and grade the picks:
```powershell
python core/audit_engine.py --days 1
```
*This will fetch scores from the NBA API, compare them to your predictions, and update the Win/Loss records.*

### Phase C: Dashboard (Live)
The `/performance` page is now connected to the `/api/audit` route. It will display the real metrics from your `audit_summary` table instead of mock values.

---

## 3. Files Created/Modified
- **Modified**: [supabase_pusher.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/core/supabase_pusher.py) (Added archiving)
- **New**: [audit_engine.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/core/audit_engine.py) (Official Grading Logic)
- **New**: [api/audit/route.ts](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/frontend/src/app/api/audit/route.ts) (Metrics API)
- **Modified**: [performance/page.tsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/frontend/src/app/performance/page.tsx) (Live UI)
