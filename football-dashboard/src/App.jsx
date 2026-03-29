import { useState, useEffect, useMemo } from 'react'
import { fetchDates, fetchPredictions, fetchLeaderboard, fetchTeamLeaderboard } from './api'
import Header from './components/Header'
import Scorecard from './components/Scorecard'
import LeagueGroup from './components/LeagueGroup'
import TeamTracker from './components/TeamTracker'

function groupByLeague(predictions, sport) {
  const map = new Map()
  for (const p of predictions) {
    const key = `${p.league_id}||${p.league}||${p.country}`
    if (!map.has(key)) map.set(key, { league: p.league, country: p.country, league_id: p.league_id, games: [] })
    map.get(key).games.push(p)
  }

  if (sport === 'basketball') {
    return [...map.values()].map(group => {
      const consolidatedMap = new Map()
      for (const game of group.games) {
        const fixtureKey = `${game.home_team}||${game.away_team}||${game.time}`
        if (!consolidatedMap.has(fixtureKey)) {
          consolidatedMap.set(fixtureKey, {
            home_team: game.home_team,
            away_team: game.away_team,
            time: game.time,
            predictions: {}
          })
        }
        const consolidated = consolidatedMap.get(fixtureKey)
        const isAdv = game.model_architecture?.includes('ADVANCED')
        if (isAdv) consolidated.predictions.adv = game
        else consolidated.predictions.srs = game

        // Sync match-level info to top level (status, scores, result)
        if (game.status) consolidated.status = game.status
        if (game.actual_home_score !== undefined) consolidated.actual_home_score = game.actual_home_score
        if (game.actual_away_score !== undefined) consolidated.actual_away_score = game.actual_away_score
        if (game.actual_result) consolidated.actual_result = game.actual_result
      }
      return { ...group, games: [...consolidatedMap.values()] }
    })
  }

  return [...map.values()]
}

function sortGroups(groups, sortBy) {
  if (sortBy === 'country')    return [...groups].sort((a, b) => a.country.localeCompare(b.country))
  if (sortBy === 'time')       return [...groups]
  return [...groups].sort((a, b) => a.league.localeCompare(b.league))
}

function filterPredictions(predictions, decision, country, drawMin, sport, leaderboard = [], maxMape = 100, maxVolatility = 100) {
  return predictions.filter(p => {
    // Sport-specific decision mapping
    const pDecision = sport === 'football' ? p.btts_decision : p.decision
    if (decision !== 'all' && pDecision !== decision) return false
    
    if (country  !== 'all' && p.country        !== country)  return false
    if (sport === 'football' && drawMin !== 0 && (p.draw_prob_1x2 ?? 0) < drawMin) return false
    
    // MAPE & Volatility Filter (Basketball only)
    if (sport === 'basketball' && (maxMape < 100 || maxVolatility < 100)) {
      const stats = leaderboard.find(x => (p.league_id && x.league_id === p.league_id) || x.name === `${p.country?.toUpperCase()} — ${p.league?.toUpperCase()}`)
      if (!stats) return false
      
      const isAdv = p.model_architecture?.includes('ADVANCED')
      const targetStats = isAdv ? stats.adv : stats.srs
      
      if (!targetStats || targetStats.graded_totals === 0) return false
      if (maxMape < 100 && targetStats.mape > maxMape) return false
      if (maxVolatility < 100 && (targetStats.volatility_index == null || targetStats.volatility_index > maxVolatility)) return false
    }
    
    return true
  })
}

export default function App() {
  const [sport,         setSport]         = useState('football')
  const [dates,         setDates]         = useState([])   // [{date,graded,...}]
  const [selectedDate,  setSelectedDate]  = useState(null)
  const [data,          setData]          = useState(null)
  const [loading,       setLoading]       = useState(false)
  const [error,         setError]         = useState(null)
  const [sortBy,        setSortBy]        = useState('competition')
  const [filterDecision,setFilterDecision]= useState('all')
  const [filterCountry, setFilterCountry] = useState('all')
  const [filterDraw,    setFilterDraw]    = useState(0)    // min draw_prob_1x2 threshold
  const [filterMape,    setFilterMape]    = useState(100)  // max error percentage
  const [filterVolatility, setFilterVolatility] = useState(100) // max standard deviation
  
  // High-level App View Mode 
  const [viewMode,      setViewMode]      = useState('matches') // 'matches' | 'teams'

  const [compactMode, setCompactMode] = useState(() => {
    const saved = localStorage.getItem('compactMode')
    if (saved !== null) return saved === 'true'
    return window.innerWidth < 1024
  })

  const [showCompactHint, setShowCompactHint] = useState(false)

  useEffect(() => {
    localStorage.setItem('compactMode', String(compactMode))
  }, [compactMode])

  useEffect(() => {
    // Show hint only on very first auto-detect run
    if (localStorage.getItem('compactMode') === null && window.innerWidth < 1024) {
      setShowCompactHint(true)
      const t = setTimeout(() => setShowCompactHint(false), 5000)
      return () => clearTimeout(t)
    }
  }, [])

  const toggleCompact = () => setCompactMode(prev => !prev)

  // ── Night Shift ──────────────────────────────────────────
  // Auto: ON between 19:00 and 06:00, manual override stored in localStorage
  function shouldAutoNightShift() {
    const h = new Date().getHours()
    return h >= 19 || h < 6  // 19:00 → 05:59
  }

  const [nightShift, setNightShift] = useState(() => {
    const manual = localStorage.getItem('nightShiftOverride')
    return manual !== null ? manual === 'true' : shouldAutoNightShift()
  })

  const [nightShiftIsAuto, setNightShiftIsAuto] = useState(
    () => localStorage.getItem('nightShiftOverride') === null
  )

  // Apply theme to body
  useEffect(() => {
    document.body.dataset.theme = nightShift ? 'dark' : 'light'
  }, [nightShift])

  // Check auto state every minute — re-sync if no manual override
  useEffect(() => {
    const tick = () => {
      if (localStorage.getItem('nightShiftOverride') === null) {
        const auto = shouldAutoNightShift()
        setNightShift(auto)
        setNightShiftIsAuto(true)
      }
    }
    tick()
    const id = setInterval(tick, 60_000)
    return () => clearInterval(id)
  }, [])

  const toggleNightShift = () => {
    setNightShift(prev => {
      const next = !prev
      localStorage.setItem('nightShiftOverride', String(next))
      setNightShiftIsAuto(false)
      return next
    })
  }
  
  const [leaderboard,   setLeaderboard]   = useState([])
  const [teamLeaderboard, setTeamLeaderboard] = useState([])
  const [showScrollTop, setShowScrollTop] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 400)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  useEffect(() => {
    setLoading(true)
    fetchDates(sport)
      .then(d => { 
        setDates(d)
        if (d.length > 0) {
          // Keep same date if possible when switching sports
          const matches = d.find(x => x.date === selectedDate)
          if (!matches) setSelectedDate(d[0].date) 
        } else {
          setSelectedDate(null)
          setData(null)
        }
        setLoading(false)
      })
      .catch(() => {
        setError(`Could not fetch ${sport} dates.`)
        setLoading(false)
      })
      
    fetchLeaderboard(sport)
      .then(d => setLeaderboard(d))
      .catch(e => console.warn(`Could not fetch ${sport} leaderboard:`, e))
      
    fetchTeamLeaderboard(sport)
      .then(d => setTeamLeaderboard(d))
      .catch(e => console.warn(`Could not fetch ${sport} team leaderboard:`, e))
      
  }, [sport])

  useEffect(() => {
    if (!selectedDate) return
    setLoading(true); setError(null); 
    fetchPredictions(selectedDate, sport)
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [selectedDate, sport])

  const countries = useMemo(() => {
    if (!data) return []
    return ['all', ...new Set(data.predictions.map(p => p.country))]
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    return filterPredictions(data.predictions, filterDecision, filterCountry, filterDraw, sport, leaderboard, filterMape, filterVolatility)
  }, [data, filterDecision, filterCountry, filterDraw, sport, leaderboard, filterMape, filterVolatility])

  const groups = useMemo(() => sortGroups(groupByLeague(filtered, sport), sortBy), [filtered, sortBy, sport])

  const counts = useMemo(() => {
    if (sport === 'football') {
      const yes    = filtered.filter(p => p.btts_decision === 'PLAY YES').length
      const no     = filtered.filter(p => p.btts_decision === 'PLAY NO' || p.btts_decision === '[STRONG] PLAY NO').length
      const strong = filtered.filter(p => p.btts_decision === '[STRONG] PLAY NO').length
      const pass   = filtered.filter(p => p.btts_decision === 'PASS').length
      return { total: filtered.length, yes, no, strong, pass }
    } else {
      const yes    = filtered.filter(p => p.decision === 'PLAY OVER').length
      const no     = filtered.filter(p => p.decision === 'PLAY UNDER').length
      const strong = filtered.filter(p => (p.edge ?? 0) > 5.0).length
      const pass   = filtered.filter(p => p.decision === 'PASS' || p.decision === 'MODEL ONLY').length
      // Count unique fixtures (not raw predictions which may include both models)
      const matchSet = new Set(filtered.map(p => `${p.home_team}||${p.away_team}||${p.time}`))
      return { total: matchSet.size, yes, no, strong, pass }
    }
  }, [filtered, sport])

  // Is this date graded at all (partially or fully)?
  const dateInfo    = dates.find(d => d.date === selectedDate)
  const hasGrading  = (dateInfo?.graded_count ?? 0) > 0

  return (
    <div className={`app ${compactMode ? 'compact-mode' : ''}`}>
      <Header 
        dates={dates} 
        selected={selectedDate} 
        onSelect={setSelectedDate} 
        sport={sport}
        setSport={(s) => { 
          setSport(s); 
          setData(null);
          setError(null);
          setFilterDecision('all'); 
          setFilterCountry('all'); 
          setFilterDraw(0); 
          setFilterMape(100);
          setFilterVolatility(100);
          setViewMode('matches');
        }}
        filterDecision={filterDecision}
        setFilterDecision={setFilterDecision}
        filterDraw={filterDraw}
        setFilterDraw={setFilterDraw}
        setFilterCountry={setFilterCountry}
        compactMode={compactMode}
        toggleCompact={toggleCompact}
        nightShift={nightShift}
        nightShiftIsAuto={nightShiftIsAuto}
        toggleNightShift={toggleNightShift}
      />
      <div className="main-wrapper">

        {/* First-time mobile hint */
         showCompactHint && (
          <div className="compact-hint fade-in-out">
            ✨ Compact mode enabled for better viewing on your device.
          </div>
        )}

        {/* Scorecard (only shown if grading data exists) */}
        {hasGrading && data && <Scorecard data={data} sport={sport} />}

        {/* API connection error — shown prominently above controls */}
        {error && !loading && (
          <div style={{ background: '#fff1f2', border: '1px solid #fecdd3', borderRadius: 8, padding: '12px 16px', marginBottom: 12, color: '#991b1b', fontWeight: 600, fontSize: 13 }}>
            ❌ {error}
          </div>
        )}

        {/* Controls row */}
        <div className="controls-bar">
          {!compactMode && (
            <div style={{ display: 'flex', background: '#f1f5f9', borderRadius: 8, padding: 4, marginRight: 16 }}>
              <button 
                onClick={() => setViewMode('matches')}
                style={{ padding: '4px 12px', fontSize: 13, fontWeight: 700, borderRadius: 6, background: viewMode === 'matches' ? '#fff' : 'transparent', color: viewMode === 'matches' ? '#0f172a' : '#64748b', boxShadow: viewMode === 'matches' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none', border: 'none', cursor: 'pointer' }}
              >
                Daily Matches
              </button>
              <button 
                onClick={() => setViewMode('teams')}
                style={{ padding: '4px 12px', fontSize: 13, fontWeight: 700, borderRadius: 6, background: viewMode === 'teams' ? '#fff' : 'transparent', color: viewMode === 'teams' ? '#0f172a' : '#64748b', boxShadow: viewMode === 'teams' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none', border: 'none', cursor: 'pointer' }}
              >
                Team Performance
              </button>
            </div>
          )}
          
          {viewMode === 'matches' && (
            <>
              <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600 }}>Sort:</span>
              {['competition', 'country', 'time'].map(s => (
                <button key={s} className={`control-btn ${sortBy === s ? 'active' : ''}`} onClick={() => setSortBy(s)}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </>
          )}

          {sport === 'football' && (
            <>
              <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600, marginLeft: 12 }}>BTTS:</span>
              <select className="filter-select" value={filterDecision} onChange={e => setFilterDecision(e.target.value)}>
                <option value="all">All decisions</option>
                <option value="PLAY YES">PLAY YES</option>
                <option value="PLAY NO">PLAY NO</option>
                <option value="[STRONG] PLAY NO">[STRONG] PLAY NO</option>
                <option value="PASS">PASS</option>
              </select>
            </>
          )}

          {sport === 'football' && (
            <>
              <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600, marginLeft: 8 }}>Draw:</span>
              <select className="filter-select" value={filterDraw} onChange={e => setFilterDraw(Number(e.target.value))}>
                <option value={0}>All draws</option>
                <option value={25}>≥ 25%</option>
                <option value={30}>≥ 30%</option>
                <option value={35}>≥ 35%</option>
                <option value={40}>≥ 40%</option>
              </select>
            </>
          )}

          {viewMode === 'matches' && sport === 'basketball' && (
            <>
              <select className="filter-select" style={{ marginLeft: 12, width: '130px' }} value={filterMape} onChange={e => setFilterMape(Number(e.target.value))}>
                <option value={100}>MAPE</option>
                <option value={10.0}>&lt; 10.0% MAPE</option>
                <option value={8.0}>&lt; 8.0% MAPE</option>
                <option value={6.5}>&lt; 6.5% MAPE</option>
                <option value={5.0}>&lt; 5.0% MAPE</option>
              </select>

              <select className="filter-select" style={{ marginLeft: 8, width: '130px' }} value={filterVolatility} onChange={e => setFilterVolatility(Number(e.target.value))}>
                <option value={100}>Volatility</option>
                <option value={14.0}>&lt; 14.0 σ</option>
                <option value={10.0}>&lt; 10.0 σ</option>
                <option value={9.0}>&lt; 9.0 σ (Elite)</option>
              </select>
            </>
          )}

          <select className="filter-select" value={filterCountry} onChange={e => setFilterCountry(e.target.value)}>
            {countries.map(c => <option key={c} value={c}>{c === 'all' ? 'All countries' : c}</option>)}
          </select>

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
            {data && viewMode === 'matches' && (
              <div className="summary-pill">
                <strong>{counts.total}</strong> games
                {sport === 'football' && (
                  <>
                    {' · '}
                    <span style={{ color: '#16a34a', fontWeight: 600 }}>{counts.yes} YES</span> ·{' '}
                    <span style={{ color: '#dc2626', fontWeight: 600 }}>{counts.no} NO</span>
                    {counts.strong > 0 && <span style={{ color: '#7f1d1d', fontWeight: 700 }}> ({counts.strong} ⚡)</span>} ·{' '}
                    <span style={{ color: '#6b7280' }}>{counts.pass} PASS</span>
                  </>
                )}
              </div>
            )}

            <div className="compact-control">
              <span className="label">Compact</span>
              <button
                className={`compact-toggle ${compactMode ? 'active' : ''}`}
                onClick={toggleCompact}
                title="Switch between full and compact layout"
              >
                <div className="toggle-track">
                  <div className="toggle-knob">
                    <span className="icon">
                      {compactMode ? '⊟' : '⊞'}
                    </span>
                  </div>
                </div>
              </button>
            </div>

            {/* Night Shift Toggle — sits next to Compact */}
            <button
              className={`night-shift-btn ${nightShift ? 'active' : ''}`}
              onClick={toggleNightShift}
              title={nightShiftIsAuto
                ? 'Night Shift: auto (ON 19:00–06:00) — click to override'
                : 'Night Shift: manual override — click to toggle'}
            >
              {nightShift ? '🌙' : '☀️'}
              {nightShiftIsAuto && <span className="night-shift-auto-label">AUTO</span>}
            </button>
          </div>

        </div>

        {loading && <div className="loading">⚽ Loading predictions…</div>}
        {error   && <div className="empty-state"><div className="icon">❌</div><p>{error}</p></div>}
        {!loading && !error && viewMode === 'matches' && groups.length === 0 && data && (
          <div className="empty-state"><div className="icon">📭</div><p>No predictions match your filters.</p></div>
        )}

        {!loading && !error && viewMode === 'teams' && (
          <TeamTracker teamLeaderboard={teamLeaderboard} />
        )}

        {!loading && !error && viewMode === 'matches' && groups.length > 0 && (
          <div className="predictions-table">
            {groups.map(g => {
              const stats = leaderboard.find(x => (g.league_id && x.league_id === g.league_id) || x.name === `${g.country?.toUpperCase()} — ${g.league?.toUpperCase()}`)
              return <LeagueGroup key={`${g.league_id}-${g.league}`} group={{...g, stats}} sport={sport} />
            })}
          </div>
        )}

        {/* Scroll to Top Button */}
        <button 
          className={`scroll-top-btn ${showScrollTop ? 'visible' : ''}`} 
          onClick={scrollToTop}
          title="Go to top"
        >
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      </div>
    </div>
  )
}
