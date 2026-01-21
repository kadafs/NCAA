# NBA Player Props v1.2 Engine
import json

class NBAPropEngine:
    """
    Advanced prop engine for NBA players.
    Implements 40/60 form weighting, usage redistribution, and defensive funnels.
    """

    def __init__(self, mode="safe"):
        self.mode = mode
        self.usage_vacuum_threshold = 15.0 # Usage pct usually, but we use PPG proxy

    def project_player(self, player_data, game_context, teammate_injuries=None):
        """
        Calculates a refined prop projection.
        """
        trace = []
        name = player_data['name']
        
        # 1. Weighted Baseline (Step 1 - Season/Recent merge)
        s = player_data['seasonal']
        r = player_data['recent']
        
        # We weigh recent 5 games at 60%, seasonal at 40%
        w_pts = (s['pts'] * 0.4) + (r['pts'] * 0.6)
        w_ast = (s['ast'] * 0.4) + (r['ast'] * 0.6)
        w_reb = (s['reb'] * 0.4) + (r['reb'] * 0.6)
        w_stl = (s.get('stl', 0) * 0.4) + (r.get('stl', 0) * 0.6)
        w_tov = (s.get('tov', 0) * 0.4) + (r.get('tov', 0) * 0.6)
        w_fgm = (s.get('fgm', 0) * 0.4) + (r.get('fgm', 0) * 0.6)
        w_fga = (s.get('fga', 0) * 0.4) + (r.get('fga', 0) * 0.6)
        w_ftm = (s.get('ftm', 0) * 0.4) + (r.get('ftm', 0) * 0.6)
        w_fta = (s.get('fta', 0) * 0.4) + (r.get('fta', 0) * 0.6)
        
        trace.append(f"Baseline (40/60): Pts {w_pts:.1f} | Reb {w_reb:.1f} | Ast {w_ast:.1f}")

        # 2. Game Environment Scaling (Step 2)
        # Scale based on team's projected total vs season avg
        factor = game_context.get('factor', 1.0)
        vol_factor = game_context.get('vol_factor', 1.0)
        
        p_pts = w_pts * factor
        p_ast = w_ast * factor
        p_reb = w_reb * vol_factor
        p_stl = w_stl * vol_factor
        p_tov = w_tov * vol_factor
        p_fgm = w_fgm * factor
        p_fga = w_fga * factor
        p_ftm = w_ftm * factor
        p_fta = w_fta * factor
        
        trace.append(f"Environment Scaling: Pts {p_pts:.1f} | Reb {p_reb:.1f} (Factor: {factor:.2f})")

        # 3. Defensive Funnel (Step 3)
        # Adjust based on opponent's allowed stats vs league avg
        opp_allowed = game_context.get('opp_allowed', {}) # e.g. {pts: 115, ast: 25, reb: 44}
        if opp_allowed:
            # League Averages (Heuristic)
            L_AVG_AST = 25.0
            L_AVG_REB = 44.0
            L_AVG_TOV = 14.5 # Opponent TOVs per game
            
            ast_mod = opp_allowed.get('ast', L_AVG_AST) / L_AVG_AST
            reb_mod = opp_allowed.get('reb', L_AVG_REB) / L_AVG_REB
            # If we had "TOV forced" by opponent, we'd use it here. 
            # For now, let's just stick to pace for STL/TOV unless we expand team stats.
            
            p_ast *= ast_mod
            p_reb *= reb_mod
            trace.append(f"Defensive Funnel: Ast x{ast_mod:.2f} | Reb x{reb_mod:.2f}")

        # 4. Usage Redistribution (The Usage Vacuum v1.3)
        bump_pts = 0
        bump_ast = 0
        bump_reb = 0
        bump_tov = 0
        if teammate_injuries:
            p_pos = player_data.get('pos', 'G').upper()
            is_guard = 'G' in p_pos
            is_big = 'F' in p_pos or 'C' in p_pos

            for inj in teammate_injuries:
                st = inj.get('status', '').lower()
                if "out" in st or "doubtful" in st:
                    # General cross-position bump
                    bump_pts += 0.05
                    
                    # Positional Bump (The "Vacuum" logic)
                    inj_pos = inj.get('pos', 'G').upper()
                    inj_is_guard = 'G' in inj_pos
                    inj_is_big = 'F' in inj_pos or 'C' in inj_pos
                    
                    if is_guard and inj_is_guard:
                        bump_pts += 0.07 
                        bump_ast += 0.15 
                        bump_tov += 0.10
                    elif is_big and inj_is_big:
                        bump_pts += 0.03
                        bump_reb += 0.15 
            
            if bump_pts > 0:
                p_pts *= (1 + bump_pts)
                p_ast *= (1 + bump_ast)
                p_reb *= (1 + bump_reb)
                p_tov *= (1 + bump_tov)
                # Volume metrics also bump with usage
                p_fga *= (1 + bump_pts * 0.8)
                p_fta *= (1 + bump_pts * 0.8)
                trace.append(f"Usage Vacuum: Pts +{bump_pts*100:.0f}% | Ast +{bump_ast*100:.0f}% | Reb +{bump_reb*100:.0f}%")

        # 5. Final Regression (v1.3 Refinement)
        prop_reg = game_context.get('prop_regression', 0.95)
        p_pts *= prop_reg
        p_ast *= prop_reg
        p_reb *= prop_reg
        p_stl *= prop_reg
        p_tov *= prop_reg
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
            "proj_tov": round(p_tov, 2),
            "proj_fgm": round(p_fgm, 2),
            "proj_fga": round(p_fga, 2),
            "proj_ftm": round(p_ftm, 2),
            "proj_fta": round(p_fta, 2),
            "seasonal": s['pts'],
            "recent": r['pts'],
            "trace": trace
        }
