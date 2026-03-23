import { useState, useEffect, useMemo } from 'react'
import { fetchDates, fetchPredictions, fetchLeaderboard } from './api'
import Header from './components/Header'
import Scorecard from './components/Scorecard'
import LeagueGroup from './components/LeagueGroup'

function groupByLeague(predictions) {
  const map = new Map()
  for (const p of predictions) {
    const key = `${p.league_id}||${p.league}||${p.country}`
    if (!map.has(key)) map.set(key, { league: p.league, country: p.country, league_id: p.league_id, games: [] })
    map.get(key).games.push(p)
  }
  return [...map.values()]
}

function sortGroups(groups, sortBy) {
  if (sortBy === 'country')    return [...groups].sort((a, b) => a.country.localeCompare(b.country))
  if (sortBy === 'time')       return [...groups]
  return [...groups].sort((a, b) => a.league.localeCompare(b.league))
}

function filterPredictions(predictions, decision, country, drawMin, sport, leaderboard = [], maxMape = 100) {
  return predictions.filter(p => {
    // Sport-specific decision mapping
    const pDecision = sport === 'football' ? p.btts_decision : p.decision
    if (decision !== 'all' && pDecision !== decision) return false
    
    if (country  !== 'all' && p.country        !== country)  return false
    if (sport === 'football' && drawMin !== 0 && (p.draw_prob_1x2 ?? 0) < drawMin) return false
    
    // MAPE Filter (Basketball only)
    if (sport === 'basketball' && maxMape < 100) {
      const stats = leaderboard.find(x => x.name === p.league.toUpperCase())
      if (!stats) return false
      
      const isAdv = p.model_architecture?.includes('ADVANCED')
      const targetStats = isAdv ? stats.adv : stats.srs
      
      if (!targetStats || targetStats.graded_totals === 0 || targetStats.mape > maxMape) {
        return false
      }
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
  
  const [leaderboard,   setLeaderboard]   = useState([])
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
    return filterPredictions(data.predictions, filterDecision, filterCountry, filterDraw, sport, leaderboard, filterMape)
  }, [data, filterDecision, filterCountry, filterDraw, sport, leaderboard, filterMape])

  const groups = useMemo(() => sortGroups(groupByLeague(filtered), sortBy), [filtered, sortBy])

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
      return { total: filtered.length, yes, no, strong, pass }
    }
  }, [filtered, sport])

  // Is this date graded at all (partially or fully)?
  const dateInfo    = dates.find(d => d.date === selectedDate)
  const hasGrading  = (dateInfo?.graded_count ?? 0) > 0

  return (
    <div>
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
        }}
        filterDecision={filterDecision}
        setFilterDecision={setFilterDecision}
        filterDraw={filterDraw}
        setFilterDraw={setFilterDraw}
        setFilterCountry={setFilterCountry}
      />
      <div className="main-wrapper">

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
          <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600 }}>Sort:</span>
          {['competition', 'country', 'time'].map(s => (
            <button key={s} className={`control-btn ${sortBy === s ? 'active' : ''}`} onClick={() => setSortBy(s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}

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

          {sport === 'basketball' && (
            <>
              <select className="filter-select" style={{ marginLeft: 12, width: '130px' }} value={filterMape} onChange={e => setFilterMape(Number(e.target.value))}>
                <option value={100}>MAPE</option>
                <option value={10.0}>&lt; 10.0% MAPE</option>
                <option value={8.0}>&lt; 8.0% MAPE</option>
                <option value={6.5}>&lt; 6.5% MAPE</option>
                <option value={5.0}>&lt; 5.0% MAPE</option>
              </select>
            </>
          )}

          <select className="filter-select" value={filterCountry} onChange={e => setFilterCountry(e.target.value)}>
            {countries.map(c => <option key={c} value={c}>{c === 'all' ? 'All countries' : c}</option>)}
          </select>

          {data && (
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
        </div>

        {loading && <div className="loading">⚽ Loading predictions…</div>}
        {error   && <div className="empty-state"><div className="icon">❌</div><p>{error}</p></div>}
        {!loading && !error && groups.length === 0 && data && (
          <div className="empty-state"><div className="icon">📭</div><p>No predictions match your filters.</p></div>
        )}

        {!loading && !error && groups.length > 0 && (
          <div className="predictions-table">
            {groups.map(g => {
              const stats = leaderboard.find(x => x.name === g.league.toUpperCase())
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
