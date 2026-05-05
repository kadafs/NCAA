import os
import json
import argparse
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'basketball')

def load_sdi_index():
    sdi_path = os.path.join(DATA_DIR, 'team_sdi.json')
    if not os.path.exists(sdi_path):
        return {}
    try:
        data = json.load(open(sdi_path, 'r', encoding='utf-8'))
        index = {}
        STOP_WORDS = {'de', 'del', 'la', 'le', 'los', 'las', 'el', 'en', 'of', 'and',
                      'the', 'bc', 'bk', 'sk', 'fc', 'ac', 'sc', 'club', 'basket',
                      'basketball', 'sport', 'sports'}

        teams = data.get('teams', [])

        # FIX: Track which first-words are shared by multiple teams.
        # A first-word shortcut is only safe when it is UNIQUE across the entire
        # SDI dataset. Common prefixes like 'maccabi', 'hapoel', 'slovan', etc.
        # must never be used as shortcut keys or they will produce false matches.
        from collections import Counter
        first_word_counts = Counter(t['team'].lower().split()[0] for t in teams if t.get('team'))
        unique_first_words = {w for w, count in first_word_counts.items() if count == 1}

        # Also track which individual meaningful words are unique
        word_index = {}   # word -> team record (only unique words)
        word_counts = Counter()
        for t in teams:
            full_key = t['team'].lower()
            for word in full_key.split():
                if len(word) >= 4 and word not in STOP_WORDS:
                    word_counts[word] += 1
        unique_words = {w for w, count in word_counts.items() if count == 1}

        for t in teams:
            full_key = t['team'].lower()
            index[full_key] = t
            words = full_key.split()

            # Only register first-word shortcut if it is unique across all teams
            first_word = words[0]
            if first_word in unique_first_words and first_word not in index:
                index[first_word] = t

            # Only register individual-word shortcuts for words unique to one team
            for word in words:
                if len(word) >= 4 and word not in STOP_WORDS and word in unique_words:
                    if word not in index:
                        index[word] = t

        return index
    except Exception:
        return {}

def get_sdi_record(team_name, sdi_index):
    if not team_name: return None
    t_lower = team_name.lower().strip()

    # 1. Exact full-name match
    rec = sdi_index.get(t_lower)
    if rec:
        return rec

    # 2. Women's suffix variant (e.g. 'Team W' -> try 'team w' key)
    words = t_lower.split()
    if t_lower.endswith(' w') or t_lower.endswith(' (w)'):
        rec = sdi_index.get(words[0] + ' w')
        if rec:
            return rec

    # 3. Unique first-word shortcut ONLY — deliberately NOT falling back to
    #    words[0] alone for multi-word names, since that causes false matches
    #    for teams sharing a common prefix (e.g. all 'Maccabi *' teams).
    #    The unique-word shortcut was already registered in load_sdi_index,
    #    so individual unique meaningful words will already resolve via key lookup.
    if len(words) == 1:
        rec = sdi_index.get(words[0])

    return rec

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, default=datetime.today().strftime('%Y-%m-%d'))
    args = parser.parse_args()
    
    pred_file = os.path.join(DATA_DIR, f'universal_predictions_{args.date}.json')
    if not os.path.exists(pred_file):
        print(f"\n[!] Error: No prediction file found for date {args.date}")
        print(f"    Run: python run_basketball_daily.py --mode full --date {args.date} --refresh")
        return
        
    sdi_index = load_sdi_index()
    if not sdi_index:
        print("\n[!] Error: team_sdi.json not found or empty.")
        print("    Run: python calculate_sdi.py")
        return
        
    with open(pred_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    predictions = data.get('predictions', [])
    if not predictions:
        print(f"\n[!] No predictions found in {pred_file}")
        return

    matches = []
    
    for p in predictions:
        ht = p.get('home_team', '')
        at = p.get('away_team', '')
        tier = p.get('tier')
        
        ht_rec = get_sdi_record(ht, sdi_index)
        at_rec = get_sdi_record(at, sdi_index)
        
        ht_sdi = ht_rec['avg_sdi'] if ht_rec else None
        at_sdi = at_rec['avg_sdi'] if at_rec else None
        
        if ht_sdi is not None and at_sdi is not None:
            combined = round((ht_sdi + at_sdi) / 2.0, 1)
        else:
            combined = None
            
        # Optional: Clean up team names if they are too long for terminal
        def clean_name(n):
            if len(n) > 22: return n[:19] + "..."
            return n
            
        matches.append({
            'home': clean_name(ht),
            'away': clean_name(at),
            'full_home': ht,
            'full_away': at,
            'league': f"{p.get('country','')} - {p.get('league','')}",
            'tier': tier,
            'ht_sdi': ht_sdi,
            'at_sdi': at_sdi,
            'combined_sdi': combined,
        })
        
    # Filter matches that have full SDI data
    valid_matches = [m for m in matches if m['combined_sdi'] is not None]
    valid_matches.sort(key=lambda x: x['combined_sdi'], reverse=True)
    
    print("\n" + "="*85)
    print(f"  DAILY SDI MATCH REPORT: {args.date}")
    print("="*85)
    print(f"  Total Matches: {len(matches)} | Full SDI Coverage: {len(valid_matches)}")
    print(f"  SDI = Star Dependency Index (Higher = More Volatile, Lower = More Balanced)")
    print("="*85)
    
    if not valid_matches:
        print("\n  [!] Could not map SDI data for any matches today.")
        return
        
    # Top 15 Most Volatile
    print("\n  [⚠️] MOST VOLATILE MATCHES (Highest Combined SDI)")
    print("  " + "-"*83)
    print(f"  {'Home Team':<22} {'Away Team':<22} {'Comb':>5} {'Tier':>5} | {'H-SDI':>5} {'A-SDI':>5}")
    print("  " + "-"*83)
    for m in valid_matches[:15]:
        tier_str = f"T{m['tier']}" if m['tier'] else "-"
        print(f"  {m['home']:<22} {m['away']:<22} {m['combined_sdi']:>4}% {tier_str:>5} | {m['ht_sdi']:>4}% {m['at_sdi']:>4}%")
        
    # Top 15 Most Stable
    print("\n\n  [🛡️] SAFEST VOLUME MATCHES (Lowest Combined SDI)")
    print("  " + "-"*83)
    print(f"  {'Home Team':<22} {'Away Team':<22} {'Comb':>5} {'Tier':>5} | {'H-SDI':>5} {'A-SDI':>5}")
    print("  " + "-"*83)
    for m in valid_matches[-15:][::-1]:
        tier_str = f"T{m['tier']}" if m['tier'] else "-"
        print(f"  {m['home']:<22} {m['away']:<22} {m['combined_sdi']:>4}% {tier_str:>5} | {m['ht_sdi']:>4}% {m['at_sdi']:>4}%")

    # High Dependency Red Flags
    red_flags = []
    for m in valid_matches:
        if m['ht_sdi'] >= 55.0:
            red_flags.append((m['full_home'], m['ht_sdi'], m['league']))
        if m['at_sdi'] >= 55.0:
            red_flags.append((m['full_away'], m['at_sdi'], m['league']))
            
    if red_flags:
        # Deduplicate
        unique_flags = {}
        for r in red_flags: unique_flags[r[0]] = r
        sorted_flags = sorted(unique_flags.values(), key=lambda x: x[1], reverse=True)
        
        print("\n\n  [🚨] INDIVIDUAL TEAM RED FLAGS (> 55% SDI)")
        print("  " + "-"*83)
        print(f"  {'Team':<25} {'SDI':>5} {'League':<40}")
        print("  " + "-"*83)
        for t, sdi, league in sorted_flags:
            if len(t) > 25: t = t[:22] + "..."
            if len(league) > 40: league = league[:37] + "..."
            print(f"  {t:<25} {sdi:>4}% {league:<40}")
            
    print("\n")

if __name__ == '__main__':
    main()
