# Universal Prop Engine v1.4
import json

class UniversalPropEngine:
    """
    League-agnostic player prop projection engine.
    Supports Positional Usage Vacuum and Defensive Funnels.
    """

    def __init__(self, mode="safe"):
        self.mode = mode.lower()

    def project_player(self, player_data, game_context, teammate_injuries=None):
        """
        Calculates projected Pts, Reb, Ast for a player.
        """
        name = player_data.get('name', 'Unknown')
        s = player_data.get('seasonal', {})
        r = player_data.get('recent', {})
        trace = []

        # 1. Weighted Baseline (40/60 Form Weighting)
        # Default weighting: 40% Season, 60% Last 5 Games
        weight_s = 0.40
        weight_r = 0.60
        
        p_pts = (s.get('pts', 0) * weight_s) + (r.get('pts', 0) * weight_r)
        p_reb = (s.get('reb', 0) * weight_s) + (r.get('reb', 0) * weight_r)
        p_ast = (s.get('ast', 0) * weight_s) + (r.get('ast', 0) * weight_r)
        p_stl = (s.get('stl', 0) * weight_s) + (r.get('stl', 0) * weight_r)
        p_blk = (s.get('blk', 0) * weight_s) + (r.get('blk', 0) * weight_r)
        p_tov = (s.get('tov', 0) * weight_s) + (r.get('tov', 0) * weight_r)
        p_threes = (s.get('threes', 0) * weight_s) + (r.get('threes', 0) * weight_r)
        p_fgm = (s.get('fgm', 0) * weight_s) + (r.get('fgm', 0) * weight_r)
        p_fga = (s.get('fga', 0) * weight_s) + (r.get('fga', 0) * weight_r)
        p_ftm = (s.get('ftm', 0) * weight_s) + (r.get('ftm', 0) * weight_r)
        p_fta = (s.get('fta', 0) * weight_s) + (r.get('fta', 0) * weight_r)
        
        trace.append(f"Baseline (40/60): Pts {p_pts:.1f} | Reb {p_reb:.1f} | Ast {p_ast:.1f} | Stl {p_stl:.1f}")

        # 2. Environment Scaling (Pace & Team Total)
        # factor = projected team score / season average score
        factor = game_context.get('factor', 1.0)
        vol_factor = game_context.get('vol_factor', 1.0) # Pace scaling
        
        p_pts *= factor
        p_reb *= vol_factor
        p_ast *= vol_factor
        p_stl *= vol_factor
        p_blk *= vol_factor
        p_tov *= vol_factor
        p_threes *= vol_factor
        p_fgm *= vol_factor
        p_fga *= vol_factor
        p_ftm *= vol_factor
        p_fta *= vol_factor
        trace.append(f"Environment Scaling: Pts {p_pts:.1f} (Factor: {factor:.2f})")

        # 3. Defensive Funnel (Opponent Weaknesses)
        allowed = game_context.get('opp_allowed', {})
        if allowed:
            # We check if the opponent allows more/less than average in each category
            # Pivot = 1.0 (Average)
            ast_mod = allowed.get('ast_pct', 1.0)
            reb_mod = allowed.get('reb_pct', 1.0)
            
            p_ast *= ast_mod
            p_reb *= reb_mod
            trace.append(f"Defensive Funnel: Ast x{ast_mod:.2f} | Reb x{reb_mod:.2f}")

        # 4. Positional Usage Redistribution (The Usage Vacuum v1.3+)
        if teammate_injuries:
            bump_pts = 0
            bump_ast = 0
            bump_reb = 0
            
            p_pos = player_data.get('pos', 'G').upper()
            is_guard = 'G' in p_pos
            is_big = 'F' in p_pos or 'C' in p_pos

            for inj in teammate_injuries:
                st = inj.get('status', '').lower()
                if "out" in st or "doubtful" in st:
                    # Generic Star Bump
                    star_pts = 0.05 
                    
                    # Positional Bump
                    inj_pos = inj.get('pos', 'G').upper()
                    inj_is_guard = 'G' in inj_pos
                    inj_is_big = 'F' in inj_pos or 'C' in inj_pos
                    
                    if is_guard and inj_is_guard:
                        bump_pts += 0.12
                        bump_ast += 0.15
                    elif is_big and inj_is_big:
                        bump_pts += 0.08
                        bump_reb += 0.15
                    else:
                        bump_pts += star_pts
            
            if bump_pts > 0:
                p_pts *= (1 + bump_pts)
                p_ast *= (1 + bump_ast)
                p_reb *= (1 + bump_reb)
                # Apply minor usage bump to other volume stats
                p_stl *= (1 + bump_pts * 0.5)
                p_tov *= (1 + bump_pts * 0.8)
                p_fgm *= (1 + bump_pts)
                p_fga *= (1 + bump_pts)
                trace.append(f"Usage Vacuum: Pts +{bump_pts*100:.0f}% applied")

        # 5. Final Regression
        prop_reg = game_context.get('prop_regression', 0.95)
        p_pts *= prop_reg
        p_ast *= prop_reg
        p_reb *= prop_reg
        p_stl *= prop_reg
        p_blk *= prop_reg
        p_tov *= prop_reg
        p_threes *= prop_reg
        p_fgm *= prop_reg
        p_fga *= prop_reg
        p_ftm *= prop_reg
        p_fta *= prop_reg
        trace.append(f"Final Prop Regression: {prop_reg}x applied")

        return {
            "name": name,
            "proj_pts": round(p_pts, 2),
            "proj_ast": round(p_ast, 2),
            "proj_reb": round(p_reb, 2),
            "proj_stl": round(p_stl, 2),
            "proj_blk": round(p_blk, 2),
            "proj_tov": round(p_tov, 2),
            "proj_3pm": round(p_threes, 2),
            "proj_fgm": round(p_fgm, 2),
            "proj_fga": round(p_fga, 2),
            "proj_ftm": round(p_ftm, 2),
            "proj_fta": round(p_fta, 2),
            "seasonal": s,
            "recent": r,
            "trace": trace
        }
