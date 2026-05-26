# Algorithmic Ghost Injury Integration (v1.0)

We have successfully rebuilt the core Proballers and Advanced Metrics engines to mathematically detect absent rotation players globally. This bridges the critical gap in tracking international lineup changes where no centralized API exists.

## 1. Upgraded Proballers Scraper
`scrape_proballers.py` has been rewritten. Its `extract_team_totals` function used to exclusively parse the final "Totals" row limitlessly. 
* It now loops through the **15 player rows** directly above the "Totals" row.
* It safely ignores DNPs/benches by only targeting rows where a player registered `>0 PTS` or played explicit minutes (ignoring empty strings, "DNP", or "00:00").
* It outputs an array of `{"name": "...", "pts": 12}` into the `{league}_proballers.json` payloads without adding any extra HTTP requests. Scraping time remains identical padding-to-padding.

## 2. Mathematical Detection Matrix
`generate_advanced_metrics.py` now includes an **Algorithmic Detector**.
When you run this script natively, it now loops through every team's games chronologically.
* It dynamically builds season-long averages for every player.
* It applies a **30% Activation Threshold**, ensuring we only care about real rotational players (ignoring a G-League call-up who played 1 game and vanished).
* It mathematically flags players if their overall Points Per Game (`PPG`) is `> 6.0` **AND** they missed the last 2 consecutive active box scores.
* It scales the penalty precisely for your `UniversalBasketballEngine` logic (`star_out`, `starter_out`, `bench_out`).

## 3. Daily Engine Injection
`run_basketball_daily.py` (around Line 610) now intercepts the dynamically generated `data/ghost_injuries_{league_id}.json` files explicitly for each exact iteration. 
* It takes those `injuries` and injects them straight into `engine.calculate_total(..., injury_notes=ghost_injuries)`!

> [!IMPORTANT]
> The algorithm is currently active, however, **there are exactly 0 Ghost Injuries right now**.
> This is because your pre-existing `proballers_{league}.json` files do not contain the newly introduced `"players"` arrays yet. 
> To test the system, simply run `python scrape_proballers.py` (or however you invoke it in your workflow) on a league. It will grab the newest games and natively inject the `"players"` data. 

> [!TIP]
> Run `python generate_advanced_metrics.py` afterward, and watch the JSON payloads populate with newly discovered injuries!
