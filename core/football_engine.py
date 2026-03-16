import math
import json
import os


def poisson_prob(lam, k):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.e ** -lam) * (lam ** k) / math.factorial(k)


def calc_outcome_probs(xg_home, xg_away, max_goals=8):
    """
    Compute 1X2 (Home Win / Draw / Away Win) probabilities via Poisson scoreline matrix.
    Returns dict with home_win, draw, away_win (all 0-1 floats, sum ~ 1.0).
    """
    home_win = draw = away_win = 0.0
    for n in range(max_goals + 1):
        ph = poisson_prob(xg_home, n)
        for m in range(max_goals + 1):
            p = ph * poisson_prob(xg_away, m)
            if n > m:
                home_win += p
            elif n == m:
                draw += p
            else:
                away_win += p
    total = home_win + draw + away_win or 1.0
    return {
        "home_win": round(home_win / total, 4),
        "draw":     round(draw     / total, 4),
        "away_win": round(away_win / total, 4),
    }


class FootballEngine:
    """
    Poisson-based BTTS + Draw prediction engine for football (soccer).

    Phase 1: Expected goals → raw BTTS and Draw probabilities (from populate.py)
    Phase 2: Sharp adjustments based on form, defensive form, BTTS history, draw tendency
    Phase 3: Edge calculation, confidence gating, output
    """

    def __init__(self, config, mode="safe", trace=False):
        self.config = config
        self.mode   = mode.lower()
        self.trace  = trace
        self._logs  = []

    def _log(self, msg):
        if self.trace:
            # encode-safe for Windows cp1252 terminals
            safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
            print(f"     > {safe_msg}")
        self._logs.append(msg)

    def calculate(self, game_data):
        """
        Main prediction entry point.
        game_data: standardized row from football/v1_0/populate.py
        Returns: dict with final probabilities, edges, decisions
        """
        c   = self.config
        sp  = c.get("sharp_params", {})

        home_name = game_data.get("home_team", "Home")
        away_name = game_data.get("away_team", "Away")
        self._log(f"Audit Session: {home_name} vs {away_name}")

        xg_home   = game_data.get("xg_home", 1.2)
        xg_away   = game_data.get("xg_away", 1.0)

        # -------------------------------------------------------
        # PHASE 1 — Base Probabilities (from Poisson, already computed)
        # -------------------------------------------------------
        btts_prob_base = game_data.get("btts_prob", 0.50)
        draw_prob_base = game_data.get("draw_prob", 0.25)

        self._log(f"Phase 1: xG {xg_home:.3f} (H) / {xg_away:.3f} (A)")
        self._log(f"Phase 1: BTTS base = {btts_prob_base*100:.1f}% | Draw base = {draw_prob_base*100:.1f}%")

        btts_adj = 0.0   # probability adjustment (additive, in percentage points)
        draw_adj = 0.0

        notes = []

        # -------------------------------------------------------
        # PHASE 2 — Sharp Adjustments (Full Mode only)
        # -------------------------------------------------------
        if self.mode == "full":
            # Sharp 1: Both teams defensive (high CS rate) → BTTS drag
            if game_data.get("is_both_defensive", False):
                drag = sp.get("defensive_btts_drag", -0.06)
                btts_adj += drag
                draw_adj += sp.get("defensive_draw_boost", 0.03)   # defensive = more draws
                self._log(f"Sharp 1: Both Defensive (CS rate H:{game_data['home_cs_rate']:.2f} A:{game_data['away_cs_rate']:.2f}) BTTS {drag:+.2f} | Draw +0.03")
                notes.append(f"Sharp: Both Defensive ({drag*100:+.1f}% BTTS)")

            # Sharp 2: Both teams attacking → BTTS boost
            if game_data.get("is_both_attacking", False):
                boost = sp.get("attacking_btts_boost", 0.05)
                btts_adj += boost
                self._log(f"Sharp 2: Both Attacking -> BTTS {boost:+.2f}")
                notes.append(f"Sharp: Both Attacking (+{boost*100:.1f}% BTTS)")

            # Sharp 3: Historical BTTS rate adjustment
            # Weight the team-specific BTTS rates vs pure Poisson
            home_btts_rate = game_data.get("home_btts_rate", 0.5)
            away_btts_rate = game_data.get("away_btts_rate", 0.5)
            historical_avg  = (home_btts_rate + away_btts_rate) / 2
            btts_historical_weight = sp.get("btts_historical_weight", 0.15)
            historical_adj  = (historical_avg - btts_prob_base) * btts_historical_weight
            btts_adj       += historical_adj
            self._log(f"Sharp 3: Historical BTTS Rate (H:{home_btts_rate:.2f} A:{away_btts_rate:.2f} avg:{historical_avg:.2f}) -> {historical_adj:+.3f}")

            # Sharp 4: Draw tendency → draw probability boost
            if game_data.get("is_draw_prone", False):
                draw_boost = sp.get("draw_prone_boost", 0.04)
                draw_adj  += draw_boost
                self._log(f"Sharp 4: Draw-Prone Teams -> Draw +{draw_boost:.2f}")
                notes.append(f"Sharp: Draw-Prone (+{draw_boost*100:.1f}% Draw)")

            # Sharp 5: Hot attacking form → BTTS boost
            combined_form = game_data.get("combined_form_wins", 4)
            if combined_form >= sp.get("form_hot_threshold", 7):
                form_boost = sp.get("form_hot_btts_boost", 0.03)
                btts_adj  += form_boost
                self._log(f"Sharp 5: Hot Form (combined {combined_form}) → BTTS +{form_boost:.2f}")
                notes.append(f"Sharp: Hot Form (+{form_boost*100:.1f}% BTTS)")
            elif combined_form <= sp.get("form_cold_threshold", 2):
                form_drag = sp.get("form_cold_btts_drag", -0.03)
                btts_adj += form_drag
                self._log(f"Sharp 5: Cold Form (combined {combined_form}) → BTTS {form_drag:.2f}")
                notes.append(f"Sharp: Cold Form ({form_drag*100:.1f}% BTTS)")

            # Sharp Cap: clamp total adjustment to prevent probability distortion
            max_adj = sp.get("max_btts_adjustment", 0.12)
            btts_adj = max(-max_adj, min(max_adj, btts_adj))
            draw_adj = max(-0.08,    min(0.08,    draw_adj))

        # -------------------------------------------------------
        # PHASE 3 — Final Probabilities & Decision
        # -------------------------------------------------------
        btts_prob_final = round(max(0.01, min(0.99, btts_prob_base + btts_adj)), 4)
        draw_prob_final = round(max(0.01, min(0.99, draw_prob_base + draw_adj)), 4)

        # Market implied probability
        btts_market_prob = c.get("btts_market_avg", 0.52)   # default to typical market

        # Edge
        btts_edge = round(btts_prob_final - btts_market_prob, 4)

        # BTTS Decision
        btts_threshold = c.get("btts_edge_threshold", 0.04)
        draw_threshold = c.get("draw_edge_threshold",  0.05)

        if btts_edge >= btts_threshold:
            btts_decision    = "PLAY YES"
            btts_confidence  = "HIGH" if btts_edge >= btts_threshold * 2 else "MEDIUM"
        elif btts_edge <= -btts_threshold:
            btts_decision    = "PLAY NO"
            btts_confidence  = "HIGH" if btts_edge <= -btts_threshold * 2 else "MEDIUM"
        else:
            btts_decision    = "PASS"
            btts_confidence  = "NO PLAY"

        # Draw: what odds do we need to have value?
        # If model says draw prob is 28%, we need odds > 1/0.28 = 3.57
        draw_fair_odds     = round(1 / draw_prob_final, 2) if draw_prob_final > 0 else 99.0
        draw_value_flag    = btts_decision == "PASS"   # flag draw only when BTTS passes

        self._log(f"Phase 3: BTTS = {btts_prob_final*100:.1f}% | Market = {btts_market_prob*100:.1f}% | Edge = {btts_edge*100:+.1f}%")
        self._log(f"Phase 3: Draw = {draw_prob_final*100:.1f}% | Fair odds = {draw_fair_odds}")
        self._log(f"Decision: BTTS {btts_decision} [{btts_confidence}]")

        # -------------------------------------------------------
        # PHASE 4 — 1X2 Outcome Prediction
        # -------------------------------------------------------
        outcome = calc_outcome_probs(xg_home, xg_away)
        hw = outcome["home_win"]
        dw = outcome["draw"]
        aw = outcome["away_win"]

        def _odds(p): return round(1 / p, 2) if p > 0 else 99.0

        # Predicted result label
        best_p = max(hw, dw, aw)
        if best_p == hw:
            predicted_result = "HOME"
        elif best_p == dw:
            predicted_result = "DRAW"
        else:
            predicted_result = "AWAY"

        self._log(f"Phase 4: Home {hw*100:.1f}% ({_odds(hw)}x)  "
                  f"Draw {dw*100:.1f}% ({_odds(dw)}x)  "
                  f"Away {aw*100:.1f}% ({_odds(aw)}x)  -> {predicted_result}")

        return {
            # Poisson outputs
            "xg_home": xg_home,
            "xg_away": xg_away,
            "xg_total": round(xg_home + xg_away, 3),

            # BTTS
            "btts_prob_base":  btts_prob_base,
            "btts_prob_final": btts_prob_final,
            "btts_market_prob": btts_market_prob,
            "btts_edge":       btts_edge,
            "btts_decision":   btts_decision,
            "btts_confidence": btts_confidence,

            # Draw (secondary)
            "draw_prob_base":  draw_prob_base,
            "draw_prob_final": draw_prob_final,
            "draw_fair_odds":  draw_fair_odds,
            "draw_value_flag": draw_value_flag,

            # 1X2
            "home_win_prob":   round(hw * 100, 1),
            "draw_prob_1x2":   round(dw * 100, 1),
            "away_win_prob":   round(aw * 100, 1),
            "home_win_odds":   _odds(hw),
            "draw_odds":       _odds(dw),
            "away_win_odds":   _odds(aw),
            "predicted_result": predicted_result,

            # Metadata
            "mode":   self.mode,
            "notes":  notes,
            "logs":   self._logs,
        }


def load_football_config(league_code):
    config_path = os.path.join("configs", "leagues", f"{league_code}.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r") as f:
        return json.load(f)

