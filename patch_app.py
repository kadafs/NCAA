import re

with open(r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\src\App.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add state variable
if 'const [filterOutcome' not in content:
    content = content.replace(
        "const [filterDecision,setFilterDecision]= useState('all')", 
        "const [filterDecision,setFilterDecision]= useState('all')\n  const [filterOutcome, setFilterOutcome] = useState('all')"
    )

# 2. Add filter parameter to filterPredictions
content = re.sub(
    r'(return filterPredictions\(data\.predictions, filterDecision,)',
    r'\1 filterOutcome,',
    content
)
content = re.sub(
    r'(filterPredictions\(predictions, decision,)',
    r'filterPredictions(predictions, decision, outcome,',
    content
)

# 3. Add to dependencies array
content = re.sub(
    r'(}, \[data, filterDecision,)',
    r'\1 filterOutcome,',
    content
)

# 4. Update Header reset props
content = content.replace(
    "setFilterDecision('all');",
    "setFilterDecision('all');\n          setFilterOutcome('all');"
)

# 5. Add filtering logic in filterPredictions
if 'if (outcome !==' not in content:
    content = re.sub(
        r'(if \(decision !== \'all\' && pDecision !== decision\) return false)',
        r'\1\n    if (outcome !== \'all\' && p.outcome_decision && !p.outcome_decision.startsWith(outcome)) return false\n    if (outcome !== \'all\' && !p.outcome_decision) return false',
        content
    )

# 6. Add UI dropdown
dropdown_jsx = '''<div className="control-group">
                <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600 }}>1X2:</span>
                <select className="filter-select" value={filterOutcome} onChange={e => setFilterOutcome(e.target.value)}>
                  <option value="all">All 1X2</option>
                  <option value="[STRONG] PLAY">[STRONG] PLAY</option>
                  <option value="PLAY">PLAY (Any)</option>
                  <option value="LEAN">LEAN</option>
                </select>
              </div>'''

if '1X2:' not in content:
    content = content.replace(
        '<div className="control-group">\n                <span style={{ fontSize: 12, color: \'#6b7280\', fontWeight: 600 }}>BTTS:</span>',
        dropdown_jsx + '\n\n              <div className="control-group">\n                <span style={{ fontSize: 12, color: \'#6b7280\', fontWeight: 600 }}>BTTS:</span>'
    )

with open(r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\src\App.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched!")
