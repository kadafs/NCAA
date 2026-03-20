import { useState } from 'react'

function fmt(v, digits = 0) {
  if (v == null || v === '-') return '—'
  return typeof v === 'number' ? v.toFixed(digits) : v
}

export default function BasketballRow({ game }) {
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('stats')

  const {
    time = '', away_team, home_team, status,
    predicted_result = '', probs_1x2 = {},
    xpts_h = 0, xpts_a = 0,
    model_total = 0, market_total, edge, side = '',
    decision = 'MODEL ONLY', confidence = '', mbet_threshold,
    home_source = 'SRS', away_source = 'SRS',
    match_center = {}
  } = game

  const { statsH = {}, statsA = {}, h2h = [], recentH = [], recentA = [], full_standings = [] } = match_center

  const tip = predicted_result === 'HOME' ? '1' : '2'
  
  // Custom decision badge color logic
  let badgeBg = '#64748b' // PASS
  if (decision === 'PLAY OVER')  badgeBg = '#15803d'
  if (decision === 'PLAY UNDER') badgeBg = '#b91c1c'
  if (decision === 'MODEL ONLY') badgeBg = '#94a3b8'

  return (
    <>
      <div 
        className={`match-row bball-grid ${open ? 'expanded' : ''}`} 
        onClick={() => setOpen(!open)}
        style={{ gridTemplateColumns: '72px 1fr 44px 22px 116px 80px 100px' }}
      >
        <div className="match-time">
          {time?.includes(' ') ? time.split(' ')[1] : time}
          {status && status !== 'Scheduled' && status !== 'Game Finished' && (
            <div className="live-indicator">{status}</div>
          )}
        </div>
        
        <div className="match-teams">
          <div className="team-row">
            <span className="team-name">{away_team} {away_source && <span className="source-flag">{away_source}</span>}</span>
          </div>
          <div className="team-row">
            <span className="team-name">{home_team}</span>
          </div>
        </div>

        {/* TIP COLUMN */}
        <div className="stat-col center divider-left">
           <div className={`tip-badge ${tip === '1' ? 'home' : 'away'}`}>{tip}</div>
        </div>

        {/* Expand chevron */}
        <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: 11, cursor: 'pointer' }}>{open ? '▲' : '▼'}</div>

        {/* 12 COLUMN */}
        <div className="stat-col center">
          <div className="prob-box-1x2">
            <div className="p-item h" style={{ width: '38px' }}>{probs_1x2.home ? Math.round(probs_1x2.home) : 0}%</div>
            <div className="p-item a" style={{ width: '38px' }}>{probs_1x2.away ? Math.round(probs_1x2.away) : 0}%</div>
          </div>
        </div>

        {/* MODEL COLUMN (Model Total) */}
        <div className="stat-col center">
          <div className="stat-val model-pct">
            {model_total > 0 ? model_total.toFixed(1) : '—'}
          </div>
        </div>

        {/* xPTS COLUMN */}
        <div className="stat-col center">
          <div className="stat-val xpts-val" style={{ whiteSpace: 'nowrap' }}>
            {xpts_a.toFixed(1)} - {xpts_h.toFixed(1)}
          </div>
        </div>
      </div>

      {open && (
        <div className="match-detail-container bball-details">
          <div className="tab-nav">
            <button className={activeTab === 'stats' ? 'active' : ''} onClick={(e) => { e.stopPropagation(); setActiveTab('stats') }}>TEAM STATS</button>
            <button className={activeTab === 'h2h' ? 'active' : ''} onClick={(e) => { e.stopPropagation(); setActiveTab('h2h') }}>LAST 5 H2H</button>
            <button className={activeTab === 'standings' ? 'active' : ''} onClick={(e) => { e.stopPropagation(); setActiveTab('standings') }}>STANDINGS</button>
            <button className={activeTab === 'probabilities' ? 'active' : ''} onClick={(e) => { e.stopPropagation(); setActiveTab('probabilities') }}>PROBABILITIES</button>
          </div>

          <div className="tab-content border-top">
            {activeTab === 'stats' && (
              <div className="tab-stats">
                <div className="stats-header">
                  <span className="sh-team">{home_team}</span>
                  <span className="sh-title">BY THE NUMBERS</span>
                  <span className="sh-team">{away_team}</span>
                </div>
                <div className="stats-body">
                  <StatRow label="Matches Played" home={statsH.played} away={statsA.played} />
                  <StatRow label="Win %" home={statsH.win_pct ? `${(statsH.win_pct * 100).toFixed(0)}%` : '-'} away={statsA.win_pct ? `${(statsA.win_pct * 100).toFixed(0)}%` : '-'} />
                  <StatRow label="Pts/Game (Model)" home={statsH.scored} away={statsA.scored} highlight="high" />
                  <StatRow label="Pts Allowed (Model)" home={statsH.conceded} away={statsA.conceded} highlight="low" />
                </div>
              </div>
            )}

            {activeTab === 'h2h' && (
              <div className="tab-h2h">
                <div className="h2h-container">
                  <div className="h2h-block">
                    <div className="h2h-section-title">Head to Head</div>
                    {h2h.length === 0 ? <div className="no-data">No recent H2H data.</div> : (
                      h2h.slice(0, 5).map((h, i) => (
                        <div key={i} className="h2h-row">
                          <div className="h2h-date">{h.date?.split('T')[0]}</div>
                          <div className="h2h-team">{h.teams.home.name}</div>
                          <div className="h2h-score">{h.scores.home.total} : {h.scores.away.total}</div>
                          <div className="h2h-team right">{h.teams.away.name}</div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="h2h-block">
                    <div className="h2h-section-title">Recent Form</div>
                    <div className="form-columns">
                      <RecentFormColumn teamName={home_team} fixtures={recentH} />
                      <RecentFormColumn teamName={away_team} fixtures={recentA} />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'standings' && (
              <div className="tab-standings">
                {!full_standings || full_standings.length === 0 ? <div className="no-data">Standings unavailable.</div> : (
                   <table className="standings-table" style={{ width: '100%', fontSize: 12 }}>
                     <thead>
                       <tr>
                         <th>#</th>
                         <th>Team</th>
                         <th>P</th>
                         <th>W-L</th>
                         <th>+/-</th>
                         <th>%</th>
                       </tr>
                     </thead>
                     <tbody>
                       {full_standings[0]?.map((s, idx) => (
                         <tr key={idx} className={(s.team.name === home_team || s.team.name === away_team) ? 'highlight' : ''}>
                           <td>{s.position}</td>
                           <td style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                             <img src={s.team.logo} width="16" height="16" alt=""/> {s.team.name}
                           </td>
                           <td>{s.games.played}</td>
                           <td>{s.games.win.total}-{s.games.lose.total}</td>
                           <td>{s.points.for - s.points.against}</td>
                           <td>{s.games.win.percentage}</td>
                         </tr>
                       ))}
                     </tbody>
                   </table>
                )}
              </div>
            )}

            {activeTab === 'probabilities' && (
              <div className="tab-probabilities">
                <div className="prob-grid">
                  <div className="prob-section full">
                    <div className="ps-title">Edge Analysis</div>
                    <div className="prob-outcome-row">
                      <div className="po-box">
                        <span className="po-val">{model_total.toFixed(1)}</span>
                        <span className="po-lbl">Model Projection</span>
                      </div>
                      <div className="po-box">
                        <span className="po-val">{market_total ? market_total.toFixed(1) : 'N/A'}</span>
                        <span className="po-lbl">Market Line</span>
                      </div>
                      <div className="po-box">
                        <span className={`po-val ${edge > 0 ? 'better' : ''}`}>{fmt(edge, 1)}</span>
                        <span className="po-lbl">Calculated Edge</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

function StatRow({ label, home, away, highlight }) {
  const hVal = parseFloat(home)
  const aVal = parseFloat(away)
  let hCls = 'sr-val', aCls = 'sr-val'
  if (!isNaN(hVal) && !isNaN(aVal)) {
    if (highlight === 'high') {
      if (hVal > aVal) hCls += ' better'
      else if (aVal > hVal) aCls += ' better'
    } else if (highlight === 'low') {
      if (hVal < aVal) hCls += ' better'
      else if (aVal < hVal) aCls += ' better'
    }
  }
  return (
    <div className="stat-row">
      <div className={hCls}>{home ?? '-'}</div>
      <div className="sr-label">{label}</div>
      <div className={aCls} style={{ textAlign: 'right' }}>{away ?? '-'}</div>
    </div>
  )
}

function RecentFormColumn({ teamName, fixtures }) {
  if (!fixtures || fixtures.length === 0) return <div className="form-column"><div className="no-data">No recent form.</div></div>
  return (
    <div className="form-column">
      <div style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', marginBottom: 6, textTransform: 'uppercase' }}>{teamName}</div>
      {fixtures.map((f, i) => {
        const isHome = f.teams.home.name === teamName
        const opp = isHome ? f.teams.away.name : f.teams.home.name
        const res = f.teams.home.winner === null ? 'D' : (isHome ? (f.teams.home.winner ? 'W' : 'L') : (f.teams.away.winner ? 'W' : 'L'))
        return (
          <div key={i} className="form-match">
            <div className={`fm-res ${res}`}>{res}</div>
            <div className="fm-opp" title={opp}>{opp}</div>
            <div className="fm-score">{f.scores.home.total}-{f.scores.away.total}</div>
          </div>
        )
      })}
    </div>
  )
}
