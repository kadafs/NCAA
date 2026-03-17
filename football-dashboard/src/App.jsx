import { useState, useEffect, useMemo } from 'react'
import { fetchDates, fetchFootball } from './api'
import Header from './components/Header'
import Navigator from './components/Navigator'
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

function filterPredictions(predictions, decision, country) {
  return predictions.filter(p => {
    if (decision !== 'all' && p.btts_decision !== decision) return false
    if (country  !== 'all' && p.country        !== country)  return false
    return true
  })
}

export default function App() {
  const [dates,         setDates]         = useState([])   // [{date,graded,...}]
  const [selectedDate,  setSelectedDate]  = useState(null)
  const [data,          setData]          = useState(null)
  const [loading,       setLoading]       = useState(false)
  const [error,         setError]         = useState(null)
  const [sortBy,        setSortBy]        = useState('competition')
  const [filterDecision,setFilterDecision]= useState('all')
  const [filterCountry, setFilterCountry] = useState('all')

  useEffect(() => {
    fetchDates()
      .then(d => { setDates(d); if (d.length > 0) setSelectedDate(d[0].date) })
      .catch(() => setError('Could not connect to API. Is the backend running?'))
  }, [])

  useEffect(() => {
    if (!selectedDate) return
    setLoading(true); setError(null); setData(null)
    fetchFootball(selectedDate)
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [selectedDate])

  const countries = useMemo(() => {
    if (!data) return []
    return ['all', ...new Set(data.predictions.map(p => p.country))]
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    return filterPredictions(data.predictions, filterDecision, filterCountry)
  }, [data, filterDecision, filterCountry])

  const groups = useMemo(() => sortGroups(groupByLeague(filtered), sortBy), [filtered, sortBy])

  const counts = useMemo(() => {
    const yes  = filtered.filter(p => p.btts_decision === 'PLAY YES').length
    const no   = filtered.filter(p => p.btts_decision === 'PLAY NO').length
    const pass = filtered.filter(p => p.btts_decision === 'PASS').length
    return { total: filtered.length, yes, no, pass }
  }, [filtered])

  // Is this date graded at all (partially or fully)?
  const dateInfo    = dates.find(d => d.date === selectedDate)
  const hasGrading  = (dateInfo?.graded_count ?? 0) > 0

  return (
    <div>
      <Header />
      <div className="main-wrapper">

        <Navigator dates={dates} selected={selectedDate} onSelect={setSelectedDate} />

        {/* Scorecard (only shown if grading data exists) */}
        {hasGrading && data && <Scorecard data={data} />}

        {/* Controls row */}
        <div className="controls-bar">
          <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600 }}>Sort:</span>
          {['competition', 'country', 'time'].map(s => (
            <button key={s} className={`control-btn ${sortBy === s ? 'active' : ''}`} onClick={() => setSortBy(s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}

          <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600, marginLeft: 12 }}>BTTS:</span>
          <select className="filter-select" value={filterDecision} onChange={e => setFilterDecision(e.target.value)}>
            <option value="all">All decisions</option>
            <option value="PLAY YES">PLAY YES</option>
            <option value="PLAY NO">PLAY NO</option>
            <option value="[STRONG] PLAY NO">[STRONG] PLAY NO</option>
            <option value="PASS">PASS</option>
          </select>

          <select className="filter-select" value={filterCountry} onChange={e => setFilterCountry(e.target.value)}>
            {countries.map(c => <option key={c} value={c}>{c === 'all' ? 'All countries' : c}</option>)}
          </select>

          {data && (
            <div className="summary-pill">
              <strong>{counts.total}</strong> games ·{' '}
              <span style={{ color: '#16a34a', fontWeight: 600 }}>{counts.yes} YES</span> ·{' '}
              <span style={{ color: '#dc2626', fontWeight: 600 }}>{counts.no} NO (incl. strong)</span> ·{' '}
              <span style={{ color: '#6b7280' }}>{counts.pass} PASS</span>
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
            {groups.map(g => (
              <LeagueGroup key={`${g.league_id}-${g.league}`} group={g} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
