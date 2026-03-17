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

export default function Scorecard({ data }) {
  const summary = data?.grade_summary
  const predictions = data?.predictions ?? []

  // Count graded games
  const graded = predictions.filter(p => p.actual_result != null)
  const pending = predictions.length - graded.length

  if (!summary && graded.length === 0) return null  // nothing to show yet

  // Compute live from predictions if summary not embedded
  const x12W = summary?.outcome_wins  ?? graded.filter(p => p.predicted_result === p.actual_result).length
  const x12T = summary?.outcome_total ?? graded.length
  const bW   = summary?.btts_wins  ?? graded.filter(p => {
    const d = p.btts_decision; const a = p.actual_btts
    return (d === 'PLAY YES' && a === true) || (d === 'PLAY NO' && a === false)
  }).length
  const bT   = summary?.btts_total ?? graded.filter(p =>
    p.btts_decision === 'PLAY YES' || p.btts_decision === 'PLAY NO'
  ).length

  const x12pct = pct(x12W, x12T)
  const bpct   = pct(bW, bT)

  return (
    <div className="scorecard">
      <div className="scorecard-title">📊 Grade Summary</div>

      <div className="scorecard-stat">
        <span className="sc-label">1X2 Outcome</span>
        <span className="sc-record">{x12W}W – {x12T - x12W}L</span>
        {x12pct != null && (
          <span className="sc-pct" style={{ color: pctColor(x12pct) }}>{x12pct}%</span>
        )}
      </div>

      <div className="scorecard-stat">
        <span className="sc-label">BTTS Plays</span>
        <span className="sc-record">{bW}W – {bT - bW}L</span>
        {bpct != null && (
          <span className="sc-pct" style={{ color: pctColor(bpct) }}>{bpct}%</span>
        )}
      </div>

      {pending > 0 && (
        <div className="sc-pending">⏳ {pending} game{pending !== 1 ? 's' : ''} pending</div>
      )}
    </div>
  )
}
