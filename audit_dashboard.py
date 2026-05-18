import streamlit as st
import pandas as pd
from run_custom_audit import get_audit_data, load_valid_leagues
import os

st.set_page_config(page_title="NCAA-API Custom Audit", page_icon="🏀", layout="wide")

# Custom CSS for styling metrics
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        border-left: 4px solid #4CAF50;
        margin-bottom: 10px;
    }
    .metric-card-red { border-left-color: #f44336; }
    .metric-card-yellow { border-left-color: #ffeb3b; }
    .metric-value { font-size: 24px; font-weight: bold; }
    .metric-label { font-size: 12px; color: #888; }
</style>
""", unsafe_allow_html=True)

st.title("🏀 Custom Team Audit")

# Load leagues (cache to avoid reloading)
@st.cache_data
def get_leagues():
    leagues = list(load_valid_leagues())
    leagues.sort(key=lambda x: int(x))
    return leagues

valid_leagues = get_leagues()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Search Mode")
    mode = st.radio("Select Mode", ["Single Team Audit", "Matchup Comparison"])
    
    st.header("Search Parameters")
    
    if mode == "Single Team Audit":
        search_term = st.text_input("Team or League Name", value="Paris")
    else:
        home_team = st.text_input("Home Team", value="Paris")
        away_team = st.text_input("Away Team", value="Lyon-Villeurbanne")
        
    use_filter = st.checkbox("Filter by League ID")
    league_filter = None
    if use_filter:
        league_filter = st.selectbox("Select League ID", valid_leagues)
        
    limit = st.slider("Recent Games Limit", min_value=0, max_value=30, value=0, help="0 means all available games since tracking epoch")
    limit_val = int(limit) if limit > 0 else None

    search_btn = st.button("Run Audit")

# --- HELPER FUNCTION: RENDER AUDIT RESULTS ---
def render_audit_results(search_term, limit_val, league_filter):
    with st.spinner(f"Fetching data for '{search_term}'..."):
        try:
            data = get_audit_data(search_term, limit=limit_val, league_id_filter=league_filter)
        except Exception as e:
            st.error(f"Error running audit for {search_term}: {e}")
            return
            
    stats = data['stats']
    games_found = data['games_found']
    sdi_matches = data['sdi_matches']
    
    if games_found == 0:
        st.warning(f"No graded games found matching '{search_term}' since the tracking epoch.")
        return
        
    st.success(f"Found {games_found} games for '{search_term}'.")
    
    if len(stats.keys()) > 1 and not league_filter:
        st.info(f"**Note:** Your search returned games across {len(stats.keys())} different leagues. Use the League ID filter to isolate performance.")
        
    tier_names = {
        1: 'Tier 1 (Both Green)',
        2: 'Tier 2 (Both Colored)',
        3: 'Tier 3 (One Unstable)',
        4: 'Tier 4 (Both Unstable)'
    }
        
    for league_name, league_stats in sorted(stats.items()):
        st.subheader(f"🏆 {league_name}")
        
        # Prepare data for a clean dataframe
        table_data = []
        
        has_ht = any(d.get('ht_count', 0) > 0 for d in league_stats.values())
        
        # Calculate overall
        total_games = 0
        total_flat = 0
        total_5 = 0
        total_10 = 0
        total_15 = 0
        total_20 = 0
        total_ht_count = 0
        total_ht_pct_sum = 0.0
        total_ht_on_pace = 0
        
        for t in range(1, 5):
            d = league_stats.get(t, {
                'total': 0, 'wins_flat': 0, 'wins_5': 0, 'wins_10': 0, 'wins_15': 0, 'wins_20': 0,
                'ht_count': 0, 'ht_pct_sum': 0.0, 'ht_on_pace': 0
            })
            tot = d['total']
            
            if tot == 0:
                row_dict = {
                    "Tier": tier_names[t], "Games": 0, "Flat Floor": "-", "-5 pts": "-", "-10 pts": "-", "-15 pts": "-", "-20 pts": "-"
                }
                if has_ht:
                    row_dict["HT Pace"] = "-"
                    row_dict["HT On-Pace"] = "-"
                table_data.append(row_dict)
                continue
                
            total_games += tot
            total_flat += d['wins_flat']
            total_5 += d['wins_5']
            total_10 += d['wins_10']
            total_15 += d.get('wins_15', 0)
            total_20 += d.get('wins_20', 0)
            total_ht_count += d.get('ht_count', 0)
            total_ht_pct_sum += d.get('ht_pct_sum', 0.0)
            total_ht_on_pace += d.get('ht_on_pace', 0)
            
            pct_flat = (d['wins_flat'] / tot) * 100
            pct_5    = (d['wins_5']    / tot) * 100
            pct_10   = (d['wins_10']   / tot) * 100
            pct_15   = (d.get('wins_15', 0) / tot) * 100
            pct_20   = (d.get('wins_20', 0) / tot) * 100
            
            row_dict = {
                "Tier": tier_names[t],
                "Games": tot,
                "Flat Floor": f"{d['wins_flat']}/{tot} ({pct_flat:.0f}%)",
                "-5 pts": f"{d['wins_5']}/{tot} ({pct_5:.0f}%)",
                "-10 pts": f"{d['wins_10']}/{tot} ({pct_10:.0f}%)",
                "-15 pts": f"{d.get('wins_15', 0)}/{tot} ({pct_15:.0f}%)",
                "-20 pts": f"{d.get('wins_20', 0)}/{tot} ({pct_20:.0f}%)"
            }
            if has_ht:
                ht_c = d.get('ht_count', 0)
                if ht_c > 0:
                    avg_ht = d['ht_pct_sum'] / ht_c
                    on_pace_pct = (d['ht_on_pace'] / ht_c) * 100
                    row_dict["HT Pace"] = f"{avg_ht:.1f}%"
                    row_dict["HT On-Pace"] = f"{d['ht_on_pace']}/{ht_c} ({on_pace_pct:.0f}%)"
                else:
                    row_dict["HT Pace"] = "-"
                    row_dict["HT On-Pace"] = "-"
            table_data.append(row_dict)
            
        # Add overall row
        if total_games > 0:
            pct_flat = (total_flat / total_games) * 100
            pct_5    = (total_5    / total_games) * 100
            pct_10   = (total_10   / total_games) * 100
            pct_15   = (total_15   / total_games) * 100
            pct_20   = (total_20   / total_games) * 100
            
            overall_dict = {
                "Tier": "OVERALL",
                "Games": total_games,
                "Flat Floor": f"{total_flat}/{total_games} ({pct_flat:.0f}%)",
                "-5 pts": f"{total_5}/{total_games} ({pct_5:.0f}%)",
                "-10 pts": f"{total_10}/{total_games} ({pct_10:.0f}%)",
                "-15 pts": f"{total_15}/{total_games} ({pct_15:.0f}%)",
                "-20 pts": f"{total_20}/{total_games} ({pct_20:.0f}%)"
            }
            if has_ht:
                if total_ht_count > 0:
                    avg_ht_overall = total_ht_pct_sum / total_ht_count
                    on_pace_overall = (total_ht_on_pace / total_ht_count) * 100
                    overall_dict["HT Pace"] = f"{avg_ht_overall:.1f}%"
                    overall_dict["HT On-Pace"] = f"{total_ht_on_pace}/{total_ht_count} ({on_pace_overall:.0f}%)"
                else:
                    overall_dict["HT Pace"] = "-"
                    overall_dict["HT On-Pace"] = "-"
            table_data.append(overall_dict)
            
        st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)
        
    # SDI Display
    if sdi_matches:
        st.markdown("---")
        st.subheader("⭐ Star Dependency Index (SDI)")
        
        # When in matchup mode, the column width is halved, so max 2 cards per row looks better
        cols_count = min(len(sdi_matches), 2) if mode == "Matchup Comparison" else min(len(sdi_matches), 3)
        sdi_cols = st.columns(cols_count)
        
        for i, rec in enumerate(sdi_matches[:cols_count]):
            with sdi_cols[i]:
                risk = rec['risk_label']
                color_class = ""
                if risk == "EXTREME": color_class = "metric-card-red"
                elif risk == "HIGH" or risk == "MODERATE": color_class = "metric-card-yellow"
                
                stars = "<br/>".join([f"• {p['name']} ({p['times_top2']}x top-2)" for p in rec.get('top_players', [])[:2]])
                
                st.markdown(f"""
                <div class="metric-card {color_class}">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 10px;">{rec['team']}</div>
                    <div class="metric-value">{rec['avg_sdi']}% SDI</div>
                    <div class="metric-label">{risk} RISK | {rec['avg_top1_pct']}% Top-1 Reliance</div>
                    <hr style="margin: 10px 0; border-color: #333;"/>
                    <div style="text-align: left; font-size: 13px; color: #ccc;">
                        {stars}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        if len(sdi_matches) > cols_count:
            st.info(f"And {len(sdi_matches) - cols_count} other matched teams not shown.")

# --- MAIN LOGIC ---
if search_btn:
    if mode == "Single Team Audit":
        if search_term:
            render_audit_results(search_term, limit_val, league_filter)
    elif mode == "Matchup Comparison":
        if home_team and away_team:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"### 🏠 Home: {home_team}")
                render_audit_results(home_team, limit_val, league_filter)
            with col2:
                st.markdown(f"### ✈️ Away: {away_team}")
                render_audit_results(away_team, limit_val, league_filter)
