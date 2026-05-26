# Empirical Hit Rate — Confidence Engine Integration

- [ ] Modify `aggregate_basketball_stats.py` to compute and store `flat_floor_hits` and `flat_floor_total` per team/league.
- [ ] Modify `run_confidence_report.py` `get_team_stats()` to return `flat_floor_hit_rate`.
- [ ] Pass hit rates into `compute_confidence()` via the game dict.
- [ ] Add `score_hit_rate()` to `core/confidence_score.py` with the Minimum approach.
- [ ] Update `compute_confidence()` to call `score_hit_rate()` and change normalization from /75 to /85.
- [ ] Update returned dict to include `hit_rate_score` and the new keys.
- [ ] Update `run_confidence_report.py` print and CSV output with the new field.
- [ ] Run `python aggregate_basketball_stats.py --regrade` to populate hit rates.
- [ ] Run `python run_confidence_report.py --no_playoffs` and verify Pesaro drops further.
