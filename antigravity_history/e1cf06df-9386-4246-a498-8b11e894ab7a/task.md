# Task: Historical Grading (March 26-30)

- [/] **Phase 1: Scout and Scrape Scores**
  - [ ] Identify active leagues for each target date.
  - [ ] Run `scrape_proballers.py` with `--daily YYYY-MM-DD` for 2026-03-26 to 2026-03-30.
- [ ] **Phase 2: Mathematical Grading (V2)**
  - [ ] Create `grade_from_proballers.py` utility.
  - [ ] Execute grading for all target dates.
  - [ ] Run `python grade_basketball.py --regrade` for each date to fix Delta fields.
- [ ] **Phase 3: Roll-up and Dashboard**
  - [ ] Run `python aggregate_basketball_stats.py`.
  - [ ] Sync to dashboard via `push_to_dashboard.py`.
