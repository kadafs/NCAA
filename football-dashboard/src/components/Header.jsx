export default function Header({ 
  dates, selected, onSelect, 
  filterDecision, setFilterDecision,
  filterDraw, setFilterDraw,
  setFilterCountry
}) {
  const selectedIdx = dates?.findIndex(d => d.date === selected) ?? -1
  const start = Math.max(0, selectedIdx - 2)
  const visible = dates?.slice(start, start + 5) || []

  const todayStr = new Date().toISOString().slice(0, 10)

  // Logic for the header filter buttons
  const isBTTSActive = filterDecision === 'PLAY YES' && filterDraw === 0
  const isDrawActive = filterDraw >= 35 && filterDecision === 'all'
  const isAllActive  = filterDecision === 'all' && filterDraw === 0

  const handleBTTS = () => { setFilterDecision('PLAY YES'); setFilterDraw(0); }
  const handleDraw = () => { setFilterDraw(35); setFilterDecision('all'); }
  const handleAll  = () => { setFilterDecision('all'); setFilterDraw(0); setFilterCountry('all'); }

  return (
    <header className="site-header">
      <div className="header-inner">
        <a href="/" className="logo">
          <img
            src="/logo.png"
            alt="blowrout — Advanced Football Prediction"
            className="logo-img"
          />
        </a>

        {visible.length > 0 && (
          <div className="header-nav">
            {visible.map(d => {
              const isToday = d.date === todayStr
              const isActive = d.date === selected
              return (
                <button
                  key={d.date}
                  className={`nav-date-tab ${isActive ? 'active' : ''}`}
                  onClick={() => onSelect(d.date)}
                >
                  {isToday ? 'Today' : d.date}
                  {d.graded && <span className="tab-check">✓</span>}
                </button>
              )
            })}
          </div>
        )}

        <div className="header-right">
          <button 
            className={`header-badge ${isBTTSActive ? 'active' : ''}`}
            onClick={handleBTTS}
          >BTTS</button>
          <button 
            className={`header-badge ${isDrawActive ? 'active' : ''}`}
            onClick={handleDraw}
          >DRAW</button>
          <button 
            className={`header-badge ${isAllActive ? 'active' : ''}`}
            onClick={handleAll}
          >ALL</button>
        </div>
      </div>
    </header>
  )
}
