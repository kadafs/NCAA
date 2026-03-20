function pct(wins, total) {
  if (!total) return null
  return Math.round((wins / total) * 100)
}

function pctColor(p) {
  if (p == null) return '#6b7280'
  if (p >= 60) return '#16a34a'
  if (p >= 45) return '#d97706'
  return '#dc2626'
}

export default function Scorecard({ data, sport = 'football' }) {
  const isFootball = sport === 'football'
  const summary = data?.grade_summary
  const predictions = data?.predictions ?? []

  // Count graded games
  const graded = predictions.filter(p => p.actual_result != null)
  const pending = predictions.length - graded.length

  if (!summary && graded.length === 0) return null  // nothing to show yet

  // Logic varies by sport
  let outcomeW, outcomeT, playW, playT, playLabel

  if (isFootball) {
    outcomeW = summary?.outcome_wins  ?? graded.filter(p => p.predicted_result === p.actual_result).length
    outcomeT = summary?.outcome_total ?? graded.length
    playW   = summary?.btts_wins  ?? graded.filter(p => {
      const d = p.btts_decision; const a = p.actual_btts
      return (d === 'PLAY YES' && a === true) || (d === 'PLAY NO' && a === false) || (d === '[STRONG] PLAY NO' && a === false)
    }).length
    playT   = summary?.btts_total ?? graded.filter(p =>
      p.btts_decision === 'PLAY YES' || p.btts_decision === 'PLAY NO' || p.btts_decision === '[STRONG] PLAY NO'
    ).length
    playLabel = "BTTS Plays"
  } else {
    // Basketball Outcome (1X2 / ML)
    outcomeW = graded.filter(p => p.predicted_result === p.actual_result).length
    outcomeT = graded.length
  }

  const outcomePct = pct(outcomeW, outcomeT)
  const playPct    = pct(playW, playT)

  return (
    <div className="scorecard">
      <div className="scorecard-title">📊 Grade Summary</div>

      <div className="scorecard-stat">
        <span className="sc-label">{isFootball ? '1X2 Outcome' : 'Winner (ML)'}</span>
        <span className="sc-record">{outcomeW}W – {outcomeT - outcomeW}L</span>
        {outcomePct != null && (
          <span className="sc-pct" style={{ color: pctColor(outcomePct) }}>{outcomePct}%</span>
        )}
      </div>

      {isFootball && (
        <div className="scorecard-stat">
          <span className="sc-label">{playLabel}</span>
          <span className="sc-record">{playW}W – {playT - playW}L</span>
          {playPct != null && (
            <span className="sc-pct" style={{ color: pctColor(playPct) }}>{playPct}%</span>
          )}
        </div>
      )}

      {pending > 0 && (
        <div className="sc-pending">⏳ {pending} game{pending !== 1 ? 's' : ''} pending</div>
      )}
    </div>
  )
}
